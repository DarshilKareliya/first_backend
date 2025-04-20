# routes/post.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from moviepy.editor import VideoFileClip
from app.db.session import SessionLocal
from app.schemas.post import PostCreate, PostOut, CommentCreate, CommentOut
from app.services import post
from app.services.auth import get_current_user
from app.services.post import get_post_data

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostOut)
def create_post(
    post_data: PostCreate,
    db: Session = Depends(lambda: SessionLocal()),
    user: dict = Depends(get_current_user),
    file: UploadFile = File(None)
):
    if file:
        try:
            # Save the uploaded file temporarily
            temp_file_path = f"app/tmp/{file.filename}"
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(file.file.read())

            # Check the video duration
            video = VideoFileClip(temp_file_path)
            if video.duration > 120:  # 120 seconds = 2 minutes
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded video exceeds the 2-minute limit."
                )
        finally:
            # Clean up the temporary file
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    post = post.create_post(db, user_id=user['id'], post_data=post_data, file=file)
    return post.get_post_data(post, db)


@router.get("/", response_model=List[PostOut])
def list_posts(db: Session = Depends(lambda: SessionLocal())):
    posts = db.query(post.Post).order_by(post.Post.created_at.desc()).all()
    return [post.get_post_data(p, db) for p in posts]


@router.post("/{post_id}/view")
def log_post_view(post_id: int, request: Request, db: Session = Depends(lambda: SessionLocal())):
    ip_address = request.client.host
    session_id = request.cookies.get("session_id") or "anonymous"
    post.log_view(db, post_id, ip_address, session_id)
    return {"message": "View logged"}


@router.post("/{post_id}/like")
def toggle_like(post_id: int, db: Session = Depends(lambda: SessionLocal()), user: dict = Depends(get_current_user)):
    post.toggle_like(db, user_id=user['id'], post_id=post_id)
    return {"message": "Toggled like"}


@router.post("/{post_id}/comment", response_model=CommentOut)
def add_comment(
    post_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(lambda: SessionLocal()),
    user: dict = Depends(get_current_user),
):
    return post.add_comment(db, user_id=user['id'], post_id=post_id, comment_data=comment_data)


@router.post("/{post_id}/share")
def share_post(post_id: int, db: Session = Depends(lambda: SessionLocal()), user: dict = Depends(get_current_user)):
    post.add_share(db, user_id=user['id'], post_id=post_id)
    return {"message": "Post shared"}


@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(lambda: SessionLocal()), user: dict = Depends(get_current_user)):
    try:
        post.delete_post(db, user_id=user['id'], post_id=post_id)
        return {"message": "Post deleted"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized or post not found")
