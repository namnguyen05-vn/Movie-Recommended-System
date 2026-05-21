"""
ML Service: Movie recommendation model with lazy loading.

Uses lazy loading to prevent blocking server startup.
Model loads on first request, subsequent requests reuse instance.
If model fails to load, graceful degradation returns trending only.
"""

import asyncio
import logging
import os
import pickle
from typing import Optional
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import create_engine
from app.db.database import engine
from app.core.config import settings

logger = logging.getLogger(__name__)


class MLService:
    """
    Singleton ML Service with lazy loading.

    First call to get_instance() loads the model.
    Subsequent calls return the loaded instance.
    If model fails to load, graceful degradation returns trending only.
    """

    _instance: Optional['MLService'] = None
    _lock = asyncio.Lock()
    _is_initialized = False

    def __init__(self):
        """Initialize but don't load model yet"""
        self.model = None
        self.movies_df = None
        self.ratings_df = None
        self.user_enc = None
        self.movie_enc = None
        self.trending_list = None
        logger.info("🔧 MLService instance created (not initialized)")

    @classmethod
    async def get_instance(cls) -> 'MLService':
        """
        Get or create ML service instance (thread-safe singleton).

        First call: Creates instance and initializes (loads model)
        Subsequent calls: Returns existing instance

        Returns:
            MLService instance (initialized or degraded mode)
        """
        if cls._instance is None:
            async with cls._lock:  # Ensure only one init
                if cls._instance is None:
                    logger.info("📦 Instantiating MLService...")
                    cls._instance = cls()
                    await cls._instance._initialize()

        return cls._instance

    async def _initialize(self):
        """
        Load model and prepare data (async).

        Runs once on first request. If fails, sets degraded mode.
        """
        try:
            logger.info("🤖 Loading ML model and data...")

            # 1. Load data from database using synchronous engine (for pandas)
            logger.info("📊 Loading data from database...")
            # Create synchronous engine for pandas (async engine doesn't work with pd.read_sql)
            sync_engine = create_engine(settings.DATABASE_URL)

            self.movies_df = pd.read_sql(
                'SELECT * FROM movies',
                con=sync_engine
            )
            if self.movies_df is not None:
                initial_count = len(self.movies_df)
            self.movies_df = self.movies_df[
                (self.movies_df['poster_url'].notna()) &
                (self.movies_df['poster_url'] != "https://via.placeholder.com/500x750?text=No+Poster")
                ]
            logger.info(f"  ✓ Lọc bỏ {initial_count - len(self.movies_df)} phim bị lỗi ảnh Poster")
            self.ratings_df = pd.read_sql(
                'SELECT * FROM ratings',
                con=sync_engine
            )
            sync_engine.dispose()  # Close synchronous connection
            logger.info(f"  ✓ Loaded {len(self.movies_df)} movies, {len(self.ratings_df)} ratings")

            # --- TẠO ĐƯỜNG DẪN TUYỆT ĐỐI TRỎ VỀ THƯ MỤC TRAINING ---
            current_dir = os.path.dirname(os.path.abspath(__file__))
            training_dir = os.path.normpath(os.path.join(current_dir, "../../training"))

            model_path = os.path.join(training_dir, 'movie_recommender_model.keras')
            user_enc_path = os.path.join(training_dir, 'user_encoder.pkl')
            movie_enc_path = os.path.join(training_dir, 'movie_encoder.pkl')
            # --------------------------------------------------------

            # 2. Load keras model (blocking I/O - run in thread pool)
            logger.info("🧠 Loading Keras model from disk...")
            import tensorflow as tf
            logger.info("🧹 Clearing Keras global session cache...")
            tf.keras.backend.clear_session()
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                load_model,
                model_path  # Sử dụng đường dẫn tuyệt đối
            )
            logger.info("  ✓ Model loaded successfully")

            # 3. Load label encoders từ file .pkl
            logger.info("🔤 Loading label encoders from disk...")
            with open(user_enc_path, 'rb') as f:
                self.user_enc = pickle.load(f)

            with open(movie_enc_path, 'rb') as f:
                self.movie_enc = pickle.load(f)
            logger.info("  ✓ Encoders loaded successfully")

            # 4. Prepare trending movies
            logger.info("📈 Calculating trending movies...")
            self._prepare_trending_movies()
            logger.info("  ✓ Trending list ready")

            self._is_initialized = True
            logger.info("✅ ML Service fully initialized!")

        except FileNotFoundError as e:
            logger.error(f"❌ Model file not found: {e}")
            logger.warning("⚠️  ML Service degraded mode: returning trending only")
            self._setup_degraded_mode()
        except Exception as e:
            logger.error(f"❌ Error initializing ML Service: {e}", exc_info=True)
            self._setup_degraded_mode()

    def _setup_degraded_mode(self):
        """Setup degraded mode when model fails to load"""
        self.model = None
        self.movies_df = None  # Clear movies_df so it will be reloaded from DB later
        self.ratings_df = None
        logger.info("🔧 MLService in degraded mode - model unavailable")

    def _reload_ratings_data(self):
        """
        Reload ratings data from database (runs in thread pool).

        Called during each recommendation request to ensure we have
        the latest ratings (including new ratings added since startup).
        """
        try:
            logger.debug("🔄 Reloading ratings data from database...")
            # Create synchronous engine for pandas reads
            sync_engine = create_engine(settings.DATABASE_URL)
            new_ratings_df = pd.read_sql(
                'SELECT * FROM ratings',
                con=sync_engine
            )
            sync_engine.dispose()  # Close connection

            old_count = len(self.ratings_df) if self.ratings_df is not None else 0
            new_count = len(new_ratings_df)

            if new_count > old_count:
                logger.debug(f"  ✓ Ratings updated: {old_count} → {new_count} ratings")
                self.ratings_df = new_ratings_df
            else:
                logger.debug(f"  ✓ Ratings data unchanged: {new_count} ratings")

        except Exception as e:
            logger.warning(f"⚠️  Could not reload ratings: {e}")
            # Continue with existing data if reload fails


    def _prepare_trending_movies(self):
        """
        Calculate trending movies based on rating count and mean.

        Trending = highly rated (mean > 4.0) + popular (count >= 50)
        Fallback: If no popular movies, return all movies with default rating
        """
        if self.ratings_df is None or self.movies_df is None:
            # Fallback: Return all movies with default rating
            self.trending_list = self.movies_df[[
                'movieId', 'title', 'genres', 'poster_url', 'description',
                'backdrop_url', 'runtime', 'director', 'cast', 'release_year', 'imdb_rating'
            ]].head(10).fillna("").to_dict(orient='records')
            # Add default predicted_rating
            for movie in self.trending_list:
                movie['predicted_rating'] = 4.0
            logger.debug(f"Trending (fallback to all movies): {len(self.trending_list)} movies")
            return

        movie_stats = self.ratings_df.groupby('movieId').agg(
            rating_count=('rating', 'count'),
            rating_mean=('rating', 'mean')
        ).reset_index()

        # Filter: at least 50 ratings, sorted by mean rating
        popular = movie_stats[
            movie_stats['rating_count'] >= 50
        ].sort_values(
            by='rating_mean',
            ascending=False
        ).head(10)  # Top 10

        if len(popular) > 0:
            popular_details = pd.merge(
                popular,
                self.movies_df,
                on='movieId'
            )

            self.trending_list = popular_details[[
                'movieId', 'title', 'genres', 'rating_mean', 'poster_url', 'description',
                'backdrop_url', 'runtime', 'director', 'cast', 'release_year', 'imdb_rating'
            ]].fillna("").rename(
                columns={'rating_mean': 'predicted_rating'}
            ).to_dict(orient='records')
        else:
            # Fallback: No movies with >= 50 ratings, return all movies
            self.trending_list = self.movies_df[[
                'movieId', 'title', 'genres', 'poster_url', 'description'
            ]].head(10).fillna("").to_dict(orient='records')
            # Add default predicted_rating
            for movie in self.trending_list:
                movie['predicted_rating'] = 4.0

        logger.debug(f"Trending: {len(self.trending_list)} movies")

    async def get_recommendations(self, user_id: int) -> dict:
        """
        Get movie recommendations for user (async wrapper).
        """
        # Ép kiểu an toàn ở mức cao nhất
        user_id = int(user_id)

        # 1. Fallback nếu thiếu Trending
        if not self.trending_list or len(self.trending_list) == 0:
            logger.debug(f"Trending list empty, loading from database for user {user_id}")
            try:
                from app.db.database import AsyncSessionLocal
                from app.services.recommendation_service import RecommendationService

                async with AsyncSessionLocal() as db:
                    recommendations = await RecommendationService._get_trending_movies(db, limit=10)
                    if recommendations and len(recommendations) > 0:
                        self.trending_list = recommendations
                        return {
                            "is_new_user": True,
                            "recommendations": recommendations,
                            "history": [],
                            "warning": "ML model unavailable, showing trending movies"
                        }
            except Exception as e:
                return {"is_new_user": True, "recommendations": [], "history": [], "error": str(e)}

        # 2. Kiểm tra Model ban đầu
        if self.model is None or not self._is_initialized:
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": [],
                "warning": "ML model temporarily unavailable, showing trending movies"
            }

        # 3. Reload Ratings để lấy dữ liệu mới nhất
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._reload_ratings_data)
        except Exception as e:
            logger.warning(f"Could not reload ratings data: {e}")

        # =========================================================
        # 4. KIỂM TRA LỊCH SỬ (ÉP KIỂU TUYỆT ĐỐI VÀ QUÉT X-QUANG)
        # =========================================================
        has_history = False
        if self.ratings_df is not None and len(self.ratings_df) > 0:
            # Ép cả 2 vế về dạng String để so sánh, vĩnh viễn chặn đứng lỗi kiểu dữ liệu
            user_id_str = str(user_id)
            self.ratings_df['userId_str'] = self.ratings_df['userId'].astype(str)

            # Lọc tìm user
            user_ratings = self.ratings_df[self.ratings_df['userId_str'] == user_id_str]
            has_history = len(user_ratings) > 0

        # NẾU LÀ NGƯỜI DÙNG HOÀN TOÀN MỚI
        if not has_history:
            logger.info(f"User {user_id} is NEW (no viewing history) - showing trending movies")
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": []
            }

        # ==============================================================
        # 🛡️ LƯỚI AN TOÀN KÉP (SELF-HEALING) - NẠP LẠI KHI CẦN THIẾT
        # ==============================================================
        if user_id not in self.user_enc.classes_:
            logger.warning(f"⚠️ Phát hiện User {user_id} bị thiếu trong AI. Bộ nhớ RAM có thể đã cũ!")
            logger.info("🔄 Kích hoạt chế độ Self-Healing: Tự động nạp lại AI từ ổ cứng...")

            # Kích hoạt tải lại toàn bộ RAM
            await self.reload_model()

            # Kiểm tra lại lần 2 sau khi nạp RAM
            if self.user_enc is None or user_id not in self.user_enc.classes_:
                logger.error(f"❌ Sau khi nạp lại, AI vẫn chưa biết User {user_id}. Buộc phải dùng Trending.")
                return {
                    "is_new_user": True,
                    "recommendations": self.trending_list or [],
                    "history": [],
                    "warning": "AI Model chưa được huấn luyện với dữ liệu của bạn."
                }
            else:
                logger.info("✅ Nạp lại RAM thành công, AI đã nhận diện được User!")
        # ==============================================================

        # 5. TIẾN HÀNH DỰ ĐOÁN (Đã đảm bảo an toàn tuyệt đối)
        try:
            logger.info(f"User {user_id} is RETURNING - generating AI recommendations")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_recommendations_sync,
                user_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ Recommendation error for user {user_id}: {e}", exc_info=True)
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": [],
                "error": "Failed to generate personalized recommendations"
            }

    def _get_recommendations_sync(self, user_id: int) -> dict:
        """Synchronous recommendation logic (runs in thread pool)"""
        watched_ids = self.ratings_df[
            self.ratings_df['userId'] == user_id
        ]['movieId'].tolist()

        all_movie_ids = self.movies_df['movieId'].unique()

        # Only recommend unwatched movies that model knows about
        unwatched = [
            m for m in all_movie_ids
            if m not in watched_ids and m in self.movie_enc.classes_
        ]

        if not unwatched:
            return {
                "is_new_user": False,
                "recommendations": self.trending_list or [],
                "history": watched_ids
            }

        # Encode and predict - Ép kiểu int một lần nữa cho an toàn
        user_encoded = self.user_enc.transform([int(user_id)])[0]
        user_input = np.array([user_encoded] * len(unwatched))
        movie_input = self.movie_enc.transform(unwatched)

        predictions = self.model.predict(
            [user_input, movie_input],
            verbose=0
        ).flatten()

        # Get top 5
        rec_df = pd.DataFrame({
            'movieId': unwatched,
            'predicted_rating': predictions
        })

        top_5 = pd.merge(
            rec_df.sort_values(
                by='predicted_rating',
                ascending=False
            ).head(5),
            self.movies_df,
            on='movieId'
        )

        return {
            "is_new_user": False,
            "recommendations": top_5[[
                'movieId', 'title', 'genres', 'predicted_rating', 'poster_url', 'description',
                'backdrop_url', 'runtime', 'director', 'cast', 'release_year', 'imdb_rating'
            ]].fillna("").to_dict(orient='records'),
            "history": watched_ids
        }

    async def reload_model(self):
        """Reload model (for admin endpoint)"""
        logger.info("🔄 Reloading ML model...")
        async with self._lock:
            self.model = None
            self._is_initialized = False
            await self._initialize()
            logger.info("✅ Model reloaded successfully")