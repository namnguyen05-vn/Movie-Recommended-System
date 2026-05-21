from pydantic import BaseModel, Field
from typing import Optional

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

class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1)
    genres: str
    description: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    runtime: Optional[int] = None
    director: Optional[str] = None
    cast: Optional[str] = None
    release_year: Optional[int] = None
    imdb_rating: Optional[float] = None

class MovieUpdate(BaseModel):
    title: Optional[str] = None
    genres: Optional[str] = None
    description: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    runtime: Optional[int] = None
    director: Optional[str] = None
    cast: Optional[str] = None
    release_year: Optional[int] = None
    imdb_rating: Optional[float] = None