from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.Post import Post, Like, Comment, Share, PostView, MediaTypeEnum
from app.schemas.post import PostCreate, PostOut, CommentCreate, CommentOut
from app.utils.time_utils import time_ago
from fastapi import UploadFile, HTTPException
import shutil, os
from typing import Optional, List, Tuple
import uuid
from app.utils.post_utils import get_post_counts, get_recent_comments

MEDIA_DIR = "app/media"


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi"}

def validate_file_extension(file: UploadFile) -> str:
    """Validates if the file has a supported extension."""
    ext = file.filename.split(".")[-1].lower()  # Get file extension in lowercase
    
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        return "video"
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported file type: {ext}. Only images and videos are allowed."
        )

def save_media(file: UploadFile) -> Tuple[str, str]:
    """Saves the uploaded media file and returns the filename and media type."""
    media_type = validate_file_extension(file)  # Validate file extension
    
    # Generate a unique filename and save the file
    filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1].lower()}"
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


def get_post_data(post: Post, db: Session) -> PostOut:
    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post.id).scalar()
    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post.id).scalar()
    share_count = db.query(func.count(Share.id)).filter(Share.post_id == post.id).scalar()
    view_count = db.query(func.count(PostView.id)).filter(PostView.post_id == post.id).scalar()
    recent_comments = db.query(Comment).filter(Comment.post_id == post.id).order_by(desc(Comment.created_at)).limit(3).all()

    return PostOut(
        id=post.id,
        user_id=post.user_id,
        username=post.user.username,
        text=post.text,
        media_url=f"/{MEDIA_DIR}/{post.media_path}" if post.media_path else None,
        media_type=post.media_type.value if post.media_type else None,
        created_at=post.created_at,
        time_ago=time_ago(post.created_at),
        like_count=like_count,
        comment_count=comment_count,
        share_count=share_count,
        view_count=view_count,
        recent_comments=recent_comments
    )

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
