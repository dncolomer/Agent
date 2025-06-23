#!/usr/bin/env python3
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

# Base class for declarative class definitions
Base = declarative_base()

class User(Base):
    """
    Represents a user in the CMS.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    posts = relationship('Post', back_populates='author')

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Post(Base):
    """
    Represents a blog post in the CMS.
    """
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    author = relationship('User', back_populates='posts')
    comments = relationship('Comment', back_populates='post')

    def __repr__(self):
        return f"<Post(title='{self.title}', author_id='{self.author_id}')>"

class Comment(Base):
    """
    Represents a comment on a blog post.
    """
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship('Post', back_populates='comments')
    author = relationship('User')

    def __repr__(self):
        return f"<Comment(post_id='{self.post_id}', author_id='{self.author_id}')>"

# Database connection setup
DATABASE_URL = "sqlite:///cms.db"  # Example for SQLite, replace with actual database URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initializes the database and creates all tables.
    """
    Base.metadata.create_all(bind=engine)

# Example usage
if __name__ == "__main__":
    init_db()