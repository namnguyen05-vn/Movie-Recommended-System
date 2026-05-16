from pydantic import BaseModel, Field
from typing import Optional

class RatingCreate(BaseModel):
    movieId: int
    rating: float = Field(..., ge=1.0, le=5.0, description="Điểm đánh giá từ 1 đến 5 sao")
class MovieResponse(BaseModel):
    movieId: int
    title: str
    genres: str
    description: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    runtime: Optional[int] = None
    director: Optional[str] = None
    cast: Optional[str] = None
    release_year: Optional[int] = None
    imdb_rating: Optional[float] = None
    predicted_rating: Optional[float] = None
    class Config:
        from_attributes = True