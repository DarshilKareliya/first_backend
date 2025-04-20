from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base

class MediaTypeEnum(enum.Enum):
    image = "image"
    video = "video"

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=True)
    media_path = Column(String, nullable=True)
    media_type = Column(Enum(MediaTypeEnum), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="posts")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    shares = relationship("Share", back_populates="post", cascade="all, delete-orphan")
    views = relationship("PostView", back_populates="post", cascade="all, delete-orphan")

class Like(Base):
    __tablename__ = 'likes'
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='unique_like'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post", back_populates="likes")

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post", back_populates="comments")

class Share(Base):
    __tablename__ = 'shares'
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='unique_share'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post", back_populates="shares")

class PostView(Base):
    __tablename__ = 'post_views'
    __table_args__ = (UniqueConstraint('post_id', 'ip_address', 'session_id', name='unique_post_view'),)

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    ip_address = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post", back_populates="views")
