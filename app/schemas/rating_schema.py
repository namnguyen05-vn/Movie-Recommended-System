from pydantic import BaseModel, Field

class RatingCreate(BaseModel):
    movieId: int
    rating: float = Field(..., ge=1.0, le=5.0, description="Điểm đánh giá từ 1 đến 5 sao")