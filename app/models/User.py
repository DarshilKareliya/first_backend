from sqlalchemy.orm import relationship
from app.db.base import Base
from sqlalchemy import Column, Integer, String, Boolean

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)
    dob = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    bio = Column(String, nullable=True)

    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", backref="user", cascade="all, delete-orphan")
    comments = relationship("Comment", backref="user", cascade="all, delete-orphan")
    shares = relationship("Share", backref="user", cascade="all, delete-orphan")
