from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.Post import Post, Like, Comment, Share, PostView

def get_post_counts(post_id: int, db: Session) -> dict:
    """Returns counts for likes, comments, shares, and views for a post."""
    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar()
    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post_id).scalar()
    share_count = db.query(func.count(Share.id)).filter(Share.post_id == post_id).scalar()
    view_count = db.query(func.count(PostView.id)).filter(PostView.post_id == post_id).scalar()
    
    return {
        "like_count": like_count,
        "comment_count": comment_count,
        "share_count": share_count,
        "view_count": view_count
    }

def get_recent_comments(post_id: int, db: Session, limit: int = 10) -> list:
    """Returns the recent comments for a post."""
    return db.query(Comment).filter(Comment.post_id == post_id).order_by(func.desc(Comment.created_at)).limit(limit).all()