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

    class Config:
        from_attributes = True