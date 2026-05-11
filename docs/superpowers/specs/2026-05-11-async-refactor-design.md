# Design Document: Complete Async Refactor - Movie Recommender API

**Date:** 2026-05-11  
**Status:** Design Phase - Awaiting Approval  
**Priority:** High (Foundational for maintainability)  
**Timeline:** No deadline, quality over speed

---

## 📋 Executive Summary

Full refactor of Movie Recommender API to improve **maintainability** through:
1. **Complete async/await** - Replace sync SQLAlchemy with async drivers
2. **Service layer** - Extract business logic from routes
3. **Centralized error handling** - Consistent API error responses
4. **Lazy ML loading** - Server starts fast, model loads on-demand
5. **Dependency injection** - Clean, testable code
6. **Comprehensive logging** - Easy debugging and monitoring

**Result:** Code that's easier to maintain, test, debug, and extend.

---

## 🎯 Goals

**Primary Objective:** Make codebase maintainable for long-term development

**Specific Goals:**
- ✅ Enable concurrent request handling (async patterns)
- ✅ Separate concerns (routes/services/db/utils)
- ✅ Reduce debugging time (centralized logging)
- ✅ Enable fast development cycles (quick testing)
- ✅ Graceful error handling (consistent responses)

---

## 🔍 Current State Analysis

### Architecture Issues

| Issue | Impact | Solution |
|-------|--------|----------|
| **Mixed concerns in routes** | Code hard to read, test impossible | Extract services |
| **ML eager loading** | Server slow to start, can't reload | Lazy load + singleton |
| **Sync DB queries** | Blocking threads, poor scalability | Async SQLAlchemy |
| **Scattered error handling** | Inconsistent responses, hard to track | Centralized middleware |
| **No logging** | Production debugging impossible | Add structured logging |
| **Blocking ML inference** | Routes stall during prediction | Run in thread pool |

### Current File Structure Issues
```
app/
├── api/           # Routes do EVERYTHING (DB, ML, validation, formatting)
├── services/      # Just MLService (and it's synchronous)
├── core/          # Config only
├── db/            # Models + database connection
└── schemas/       # Pydantic models (good)

Problems:
- No error handling layer
- No dependency injection setup
- No utils/decorators for common patterns
- No middleware configuration
```

---

## 📐 New Architecture Design

### Directory Structure (After Refactor)

```
app/
├── api/
│   ├── __init__.py
│   ├── auth.py                    # [UPDATE] Async routes
│   ├── movies.py                  # [UPDATE] Async routes
│   ├── recommend.py               # [UPDATE] Async routes
│   └── health.py                  # [NEW] Health check
│
├── core/
│   ├── __init__.py
│   ├── config.py                  # [UPDATE] Add ASYNC_DATABASE_URL
│   ├── security.py                # [NO CHANGE] JWT, password hashing
│   ├── exceptions.py              # [NEW] Custom exception classes
│   └── constants.py               # [NEW] Magic strings, enums
│
├── db/
│   ├── __init__.py
│   ├── database.py                # [UPDATE] Async engine + sessionmaker
│   ├── models.py                  # [NO CHANGE] ORM models
│   └── dependencies.py            # [NEW] Async session dependency
│
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py           # [NEW] Global error handling
│   └── logging_middleware.py      # [NEW] Request/response logging
│
├── services/
│   ├── __init__.py
│   ├── ml_service.py              # [UPDATE] Async + lazy loading
│   ├── user_service.py            # [NEW] User business logic
│   ├── movie_service.py           # [NEW] Movie business logic
│   └── recommendation_service.py  # [NEW] Recommendation logic
│
├── schemas/
│   ├── __init__.py
│   ├── base_schema.py             # [NEW] Base response schemas
│   ├── user_schema.py             # [NO CHANGE] User validation
│   ├── movie_schema.py            # [NO CHANGE] Movie validation
│   └── error_schema.py            # [NEW] Error response format
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                  # [NEW] Logging configuration
│   ├── validators.py              # [NEW] Reusable validators
│   └── decorators.py              # [NEW] Caching, retry logic
│
├── __init__.py
└── main.py                        # [UPDATE] Async app + lifespan
```

---

## 🔧 Design Sections

### Section 1: Project Structure & Separation of Concerns

**Principle:** Each module has ONE clear responsibility

**Current Problem:**
```python
# api/auth.py
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # ❌ Does EVERYTHING:
    # - Validate input (should be automatic via Pydantic)
    # - Check DB for dupes (DB concern)
    # - Hash password (security concern)
    # - Create user (DB concern)
    # - Format response (API concern)
```

**Solution:** Separate layers

```python
# api/auth.py (HTTP layer - ONLY handles HTTP/JSON)
@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        result = await user_service.register_user(user.username, user.password, db)
        return UserResponse.from_orm(result)
    except DuplicateUserError as e:
        raise HTTPException(status_code=409, detail=e.message)

# services/user_service.py (Business logic layer)
class UserService:
    @staticmethod
    async def register_user(username: str, password: str, db: AsyncSession) -> User:
        # Check if exists
        if await db.execute(select(User).where(User.username == username)):
            raise DuplicateUserError(f"Username {username} already taken")
        
        # Create + save
        user = User(username=username, password_hash=get_password_hash(password))
        db.add(user)
        await db.commit()
        return user

# core/exceptions.py (Error definitions)
class AppError(Exception):
    status_code: int
    error_type: str
    message: str

class DuplicateUserError(AppError):
    status_code = 409
    error_type = "DUPLICATE_USER"
```

**Benefits:**
- ✅ Services testable without HTTP (mock db only)
- ✅ Routes are thin and readable
- ✅ Error messages consistent
- ✅ Easy to reuse service for CLI, scripts, etc.

---

### Section 2: Async Database Architecture

**Paradigm Shift:** From synchronous blocking to asynchronous non-blocking I/O

**Driver Change:**
```
Before: mysql+pymysql://  (synchronous)
After:  mysql+aiomysql://  (async - non-blocking)
```

**Configuration:**
```python
# core/config.py
class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mysql+aiomysql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
```

**Database Setup:**
```python
# db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"timeout": 10}
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**Session Dependency:**
```python
# db/dependencies.py
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Query Pattern (before vs after):**

Before (Blocking):
```python
user = db.query(User).filter(User.userId == user_id).first()  # 50ms - BLOCKS thread
```

After (Non-blocking):
```python
result = await db.execute(
    select(User).where(User.userId == user_id)
)
user = result.scalars().first()  # 50ms - Yields thread to 100 other requests
```

**Benefits:**
- ✅ 1 thread handles 100 concurrent users (instead of 100 threads for 100 users)
- ✅ Better resource usage
- ✅ Scales with demand

---

### Section 3: ML Service - Lazy Loading & Singleton

**Problem with Current Approach:**
```python
# services/ml_service.py - Line 87
ml_logic = MLService()  # ❌ BLOCKS 3-5 seconds on import!
```

**Issues:**
- Server takes 3-5 seconds to start (bad for testing, deploys)
- Can't reload model without server restart
- If model file missing → server crash

**Solution: Lazy Loading + Singleton**

```python
class MLService:
    _instance: Optional['MLService'] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls) -> 'MLService':
        """Thread-safe lazy loader"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """Load model + data (runs once)"""
        # Load from DB, disk
        # Prepare encoders
        # Build trending list
    
    async def get_recommendations(self, user_id: int) -> dict:
        """Async wrapper - never blocks"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_recommendations_sync,
            user_id
        )
```

**Startup Flow (improved):**

Before:
```
python main.py
  ↓
import ml_service
  ↓
ml_logic = MLService()  ← CHẶN 3-5 giây
  ↓
Server ready
```

After:
```
python main.py
  ↓
lifespan@startup
  ↓
asyncio.create_task(MLService.get_instance())  ← Background, không block
  ↓
Server ready (0.5 giây)
  ↓
First /recommend request
  ↓
get_ml_service() ← Nếu ready, dùng; chưa thì chờ 1-2 giây
```

**Graceful Degradation:**
- If model fails to load → return trending movies only
- Server doesn't crash
- Admin can reload model via endpoint

---

### Section 4: Centralized Error Handling

**Current:** Errors scattered, inconsistent

```python
# ❌ Inconsistent error handling
raise HTTPException(status_code=400, detail="Username taken")
raise HTTPException(status_code=401, detail="Wrong password")
raise HTTPException(status_code=500, detail="Database error")
```

**Solution: Custom exceptions + middleware**

```python
# core/exceptions.py
class AppError(Exception):
    status_code: int
    error_type: str
    message: str

class DuplicateUserError(AppError):
    status_code = 409
    error_type = "DUPLICATE_USER"

class AuthenticationError(AppError):
    status_code = 401
    error_type = "INVALID_CREDENTIALS"

# middleware/error_handler.py
@app.exception_handler(AppError)
async def handle_app_error(request, exc: AppError):
    logger.warning(
        f"App error: {exc.error_type}",
        extra={"user": request.user_id, "path": request.url.path}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "type": exc.error_type,
            "timestamp": datetime.now().isoformat()
        }
    )

# Usage
@router.post("/login")
async def login(user: UserCreate):
    if not user_exists:
        raise AuthenticationError("Invalid username or password")
    # Error automatically formatted by middleware
```

**Response Format:**
```json
{
  "error": "Invalid username or password",
  "type": "INVALID_CREDENTIALS",
  "timestamp": "2026-05-11T10:30:00"
}
```

**Benefits:**
- ✅ Frontend knows error type → can handle specially
- ✅ Monitoring/logging can categorize errors
- ✅ Consistent across entire API

---

### Section 5: Dependency Injection & Testing

**Pattern:** FastAPI's `Depends()` + generator functions

```python
# db/dependencies.py
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    token: str = Depends(HTTPBearer())
) -> User:
    return decode_token(token)

async def get_ml_service() -> MLService:
    return await MLService.get_instance()

# Usage in routes
@router.post("/login")
async def login(
    credentials: UserCreate,
    db: AsyncSession = Depends(get_db_session),  # Auto open/close
):
    user = await user_service.authenticate(credentials.username, credentials.password, db)
    return {"access_token": create_token(user.userId)}
```

**Testing:**
```python
# tests/test_auth.py
@pytest.mark.asyncio
async def test_register_duplicate_user():
    # Create mock DB
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = User(username="existing")
    
    # Test
    with pytest.raises(DuplicateUserError):
        await user_service.register_user("existing", "password123", mock_db)
    
    # No need for real database!
```

---

### Section 6: Structured Logging

**Current:** No logging (dangerous!)

**Solution:** Structured logging at every important point

```python
# utils/logger.py
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Usage
@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db_session)):
    logger.info("register_attempt", extra={"username": user.username})
    
    try:
        result = await user_service.register_user(user.username, user.password, db)
        logger.info("register_success", extra={"user_id": result.userId, "username": user.username})
        return result
    except DuplicateUserError as e:
        logger.warning("register_failed_duplicate", extra={"username": user.username})
        raise
```

**Log Output:**
```json
{"message": "register_attempt", "username": "john_doe", "timestamp": "2026-05-11T10:30:00"}
{"message": "register_success", "user_id": 123, "username": "john_doe", "timestamp": "2026-05-11T10:30:01"}
```

---

## 📦 Dependencies & Requirements

**New Dependencies to Add:**
```
sqlalchemy[asyncio]==2.0.23      # Already have, now async
aiomysql==0.2.0                  # Async MySQL driver
aiosqlite==3.0.0                 # For testing (optional)
python-json-logger==2.0.7        # Structured logging
pydantic-settings==2.0.3         # Already have
```

**Updated requirements.txt:**
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy[asyncio]==2.0.23
aiomysql==0.2.0
pydantic==2.5.0
pydantic-settings==2.0.3
python-json-logger==2.0.7
tensorflow==2.13.0
scikit-learn==1.3.0
pandas==2.0.3
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
```

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT REQUEST (HTTP POST /api/register)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
      ┌──────────────────────────────────────┐
      │ middleware/logging_middleware.py     │
      │ - Log request received               │
      │ - Add request_id                     │
      └──────────────────────┬───────────────┘
                             │
                             ▼
      ┌──────────────────────────────────────┐
      │ api/auth.py                          │
      │ @router.post("/register")            │
      │ - Parse JSON (Pydantic validates)    │
      │ - Call service                       │
      └──────────────────────┬───────────────┘
                             │
                             ▼
      ┌──────────────────────────────────────┐
      │ Dependency Injection                 │
      │ - get_db_session() → AsyncSession    │
      │ - Check duplicate in DB              │
      └──────────────────────┬───────────────┘
                             │
                             ▼
      ┌──────────────────────────────────────┐
      │ services/user_service.py             │
      │ async def register_user()            │
      │ - Validate business rules            │
      │ - Hash password                      │
      │ - Create user object                 │
      │ - Save to DB                         │
      └──────────────────────┬───────────────┘
                             │
      ┌──────────────┬──────────────┬──────────────┐
      │ Success      │ DB Error     │ Validation   │
      │              │              │ Error        │
      ▼              ▼              ▼
   [Commit]   [Rollback]    [Validation Error]
      │              │              │
      └──────────────┼──────────────┘
                     │
                     ▼
      ┌──────────────────────────────────────┐
      │ middleware/error_handler.py          │
      │ @app.exception_handler(AppError)     │
      │ - Catch errors                       │
      │ - Format response                    │
      │ - Log failure                        │
      └──────────────────────┬───────────────┘
                             │
                             ▼
      ┌──────────────────────────────────────┐
      │ middleware/logging_middleware.py     │
      │ - Log response                       │
      │ - Add duration                       │
      └──────────────────────┬───────────────┘
                             │
                             ▼
      ┌──────────────────────────────────────┐
      │ CLIENT (JSON response)               │
      │ 201 Created or 4xx/5xx               │
      └──────────────────────────────────────┘
```

---

## 📋 Implementation Checklist

**Phase 1: Core Infrastructure (Days 1-2)**
- [ ] Add async dependencies to requirements.txt
- [ ] Create core/exceptions.py
- [ ] Update db/database.py (async engine)
- [ ] Create db/dependencies.py (async session)
- [ ] Update core/config.py (ASYNC_DATABASE_URL)
- [ ] Create middleware/error_handler.py
- [ ] Create utils/logger.py

**Phase 2: Service Layer (Days 3-4)**
- [ ] Create services/user_service.py
- [ ] Create services/movie_service.py
- [ ] Create services/recommendation_service.py
- [ ] Update services/ml_service.py (lazy loading)
- [ ] Create db/dependencies.py (ML service dependency)

**Phase 3: Routes Refactor (Days 5-6)**
- [ ] Update api/auth.py (async routes)
- [ ] Update api/movies.py (async routes)
- [ ] Update api/recommend.py (async routes)
- [ ] Create api/health.py (health check)
- [ ] Update app/main.py (lifespan event)

**Phase 4: Testing & Docs (Days 7-8)**
- [ ] Write tests/ for each service
- [ ] Write README.md (architecture overview)
- [ ] Write DEVELOPMENT.md (setup for devs)
- [ ] Integration testing (all layers)

---

## ✅ Success Criteria

**Code Quality:**
- ✅ 0 blocking I/O in routes (all async/await)
- ✅ 100% custom exceptions caught by middleware
- ✅ Every function has 1 clear responsibility
- ✅ All dependencies injected (not global state)

**Maintainability:**
- ✅ New dev can understand routes in <5 minutes
- ✅ New feature requires changes in ≤3 files
- ✅ Service logic testable without DB/FastAPI
- ✅ Error messages clear to frontend

**Performance:**
- ✅ Server starts in <1 second (was 3-5s)
- ✅ Handle 100 concurrent requests on 1-2 threads
- ✅ ML model loads in background, doesn't block routes

**Operations:**
- ✅ Debug production via structured logs
- ✅ Errors categorized (error_type field)
- ✅ Can reload ML model without server restart
- ✅ Graceful degradation if ML fails

---

## 📚 References

**Files to Review:**
- Current: `app/services/ml_service.py` (line 87)
- Current: `app/api/auth.py` (mixed concerns)
- Current: `app/db/database.py` (sync setup)

**Technologies:**
- FastAPI async: https://fastapi.tiangolo.com/async-sql-databases/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Python async/await: https://docs.python.org/3/library/asyncio.html

---

## 🎯 Next Steps

1. User reviews + approves this design document
2. Run spec self-review (check for ambiguities)
3. Invoke writing-plans skill → Create detailed implementation plan
4. Begin Phase 1 implementation

---

**Status:** ✋ Awaiting user review and approval

