"""
ML Service: Movie recommendation model with lazy loading.

Uses lazy loading to prevent blocking server startup.
Model loads on first request, subsequent requests reuse instance.
If model fails to load, graceful degradation returns trending only.
"""

import asyncio
import logging
from typing import Optional
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import LabelEncoder
from app.db.database import engine

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
            
            # 1. Load data from database
            logger.info("📊 Loading data from database...")
            self.movies_df = pd.read_sql(
                'SELECT * FROM movies', 
                con=engine
            )
            self.ratings_df = pd.read_sql(
                'SELECT * FROM ratings', 
                con=engine
            )
            logger.info(f"  ✓ Loaded {len(self.movies_df)} movies, {len(self.ratings_df)} ratings")
            
            # 2. Load keras model (blocking I/O - run in thread pool)
            logger.info("🧠 Loading Keras model from disk...")
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                load_model,
                'ml_models/movie_recommender_model.keras'
            )
            logger.info("  ✓ Model loaded successfully")
            
            # 3. Prepare label encoders
            logger.info("🔤 Preparing label encoders...")
            self.user_enc = LabelEncoder()
            self.movie_enc = LabelEncoder()
            self.user_enc.fit(self.ratings_df['userId'])
            self.movie_enc.fit(self.ratings_df['movieId'])
            logger.info("  ✓ Encoders ready")
            
            # 4. Prepare trending movies
            logger.info("📈 Calculating trending movies...")
            self._prepare_trending_movies()
            logger.info("  ✓ Trending list ready")
            
            MLService._is_initialized = True
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
        self.trending_list = []  # Will be populated from DB on first request
        logger.info("🔧 MLService in degraded mode - model unavailable")

    
    def _prepare_trending_movies(self):
        """
        Calculate trending movies based on rating count and mean.
        
        Trending = highly rated (mean > 4.0) + popular (count >= 50)
        """
        if self.ratings_df is None or self.movies_df is None:
            self.trending_list = []
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
                'movieId', 'title', 'genres', 'rating_mean', 'poster_url', 'description'
            ]].fillna("").rename(
                columns={'rating_mean': 'predicted_rating'}
            ).to_dict(orient='records')
        else:
            self.trending_list = []
        
        logger.debug(f"Trending: {len(self.trending_list)} movies")
    
    async def get_recommendations(self, user_id: int) -> dict:
        """
        Get movie recommendations for user (async wrapper).
        
        Args:
            user_id: User's ID
            
        Returns:
            {
                "is_new_user": bool,
                "recommendations": [{movieId, title, genres, predicted_rating, ...}],
                "history": []
            }
        """
        # If model not initialized
        if self.model is None or not self._is_initialized:
            logger.warning(f"⚠️  Model unavailable for user {user_id}, returning trending")
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": [],
                "warning": "ML model temporarily unavailable, showing trending movies"
            }
        
        # New user (ID outside train set)
        if user_id > 610:  # Assuming training data has max user ID of 610
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": []
            }
        
        try:
            # Run inference in thread pool (it's CPU-intensive)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_recommendations_sync,
                user_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ Recommendation error for user {user_id}: {e}", exc_info=True)
            # Graceful fallback
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
        
        # Encode and predict
        user_encoded = self.user_enc.transform([user_id])[0]
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
                'movieId', 'title', 'genres', 'predicted_rating', 'poster_url', 'description'
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
