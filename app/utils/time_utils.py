from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.Post import Post, Like, Comment, Share, PostView, MediaTypeEnum
from app.schemas.post import PostCreate, PostOut, CommentCreate, CommentOut
from fastapi import UploadFile
import shutil, os
from typing import Optional, List, Tuple
import uuid

MEDIA_DIR = "media"


def save_media(file: UploadFile) -> Tuple[str, str]:
    ext = file.filename.split(".")[-1]
    media_type = "video" if ext in ["mp4", "mov", "avi"] else "image"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(MEDIA_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filename, media_type


def create_post(db: Session, user_id: int, post_data: PostCreate, file: Optional[UploadFile]) -> Post:
    filename, media_type = (None, None)
    if file:
        filename, media_type = save_media(file)
    post = Post(user_id=user_id, text=post_data.text, media_path=filename, media_type=media_type)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post




def log_view(db: Session, post_id: int, ip_address: str, session_id: str):
    already_viewed = db.query(PostView).filter_by(post_id=post_id, ip_address=ip_address, session_id=session_id).first()
    if not already_viewed:
        db.add(PostView(post_id=post_id, ip_address=ip_address, session_id=session_id))
        db.commit()


def add_comment(db: Session, user_id: int, post_id: int, comment_data: CommentCreate) -> Comment:
    comment = Comment(user_id=user_id, post_id=post_id, text=comment_data.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def toggle_like(db: Session, user_id: int, post_id: int):
    like = db.query(Like).filter_by(user_id=user_id, post_id=post_id).first()
    if like:
        db.delete(like)
    else:
        like = Like(user_id=user_id, post_id=post_id)
        db.add(like)
    db.commit()


def add_share(db: Session, user_id: int, post_id: int):
    share = db.query(Share).filter_by(user_id=user_id, post_id=post_id).first()
    if not share:
        db.add(Share(user_id=user_id, post_id=post_id))
        db.commit()


def delete_post(db: Session, user_id: int, post_id: int):
    post = db.query(Post).filter_by(id=post_id, user_id=user_id).first()
    if not post:
        raise ValueError("Post not found or not authorized")
    if post.media_path:
        try:
            os.remove(os.path.join(MEDIA_DIR, post.media_path))
        except FileNotFoundError:
            pass
    db.delete(post)
    db.commit()

from datetime import datetime, timedelta

def time_ago(dt: datetime) -> str:
    now = datetime.utcnow()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
