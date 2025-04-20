from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CommentOut(BaseModel):
    id: int
    user_id: int
    text: str
    created_at: datetime

    class Config:
        orm_mode = True

class PostCreate(BaseModel):
    text: Optional[str] = None

class PostOut(BaseModel):
    id: int
    user_id: int
    username: str
    text: Optional[str]
    media_url: Optional[str]
    media_type: Optional[str]
    created_at: datetime
    time_ago: str
    like_count: int
    comment_count: int
    share_count: int
    view_count: int
    recent_comments: List[CommentOut]

    class Config:
        orm_mode = True

class CommentCreate(BaseModel):
    text: str
