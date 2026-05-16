from pydantic import BaseModel

class FavoriteToggleRequest(BaseModel):
    movieId: int

class FavoriteStatusResponse(BaseModel):
    is_favorite: bool