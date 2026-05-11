"""
Custom exception classes for the application.

All exceptions inherit from AppError, which provides:
- status_code: HTTP status code
- error_type: Machine-readable error type for frontend
- message: Human-readable error message
"""


class AppError(Exception):
    """
    Base application error class.
    
    All app-specific exceptions inherit from this.
    Middleware catches AppError and formats it as JSON.
    """
    status_code: int = 400
    error_type: str = "UNKNOWN_ERROR"
    message: str = ""
    
    def __init__(self, message: str = ""):
        self.message = message or self.__class__.message
        super().__init__(self.message)


# Authentication & User Errors
class DuplicateUserError(AppError):
    """User already exists"""
    status_code = 409
    error_type = "DUPLICATE_USER"


class UserNotFoundError(AppError):
    """User does not exist"""
    status_code = 404
    error_type = "USER_NOT_FOUND"


class InvalidCredentialsError(AppError):
    """Username or password incorrect"""
    status_code = 401
    error_type = "INVALID_CREDENTIALS"


# Token & Security Errors
class InvalidTokenError(AppError):
    """JWT token invalid or expired"""
    status_code = 401
    error_type = "INVALID_TOKEN"


class TokenExpiredError(AppError):
    """JWT token has expired"""
    status_code = 401
    error_type = "TOKEN_EXPIRED"


# Movie & Recommendation Errors
class MovieNotFoundError(AppError):
    """Movie does not exist"""
    status_code = 404
    error_type = "MOVIE_NOT_FOUND"


class RecommendationError(AppError):
    """Error generating recommendations"""
    status_code = 500
    error_type = "RECOMMENDATION_FAILED"


class MLServiceUnavailableError(AppError):
    """ML model not loaded"""
    status_code = 503
    error_type = "ML_SERVICE_UNAVAILABLE"


# Database Errors
class DatabaseError(AppError):
    """Database operation failed"""
    status_code = 500
    error_type = "DATABASE_ERROR"


class DatabaseConnectError(DatabaseError):
    """Cannot connect to database"""
    error_type = "DATABASE_CONNECT_ERROR"


# Validation Errors
class ValidationError(AppError):
    """Input validation failed"""
    status_code = 422
    error_type = "VALIDATION_ERROR"


# Generic Server Error
class InternalServerError(AppError):
    """Unexpected server error"""
    status_code = 500
    error_type = "INTERNAL_SERVER_ERROR"

