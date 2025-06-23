#!/usr/bin/env python3
"""
Database models for the content management system.

This module defines the database models and schema for the CMS application.
It uses the SQLAlchemy ORM to interact with the database.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    """
    Model representing a user in the CMS.

    Attributes:
        id (int): The unique identifier for the user.
        username (str): The user's username.
        email (str): The user's email address.
        password (str): The hashed password for the user.
        posts (list): A list of Post objects created by the user.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(120), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    posts = relationship('Post', backref='author', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

class Post(Base):
    """
    Model representing a blog post in the CMS.

    Attributes:
        id (int): The unique identifier for the post.
        title (str): The title of the post.
        content (str): The content of the post.
        date_posted (datetime): The date and time the post was created.
        user_id (int): The ID of the user who created the post.
    """
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    date_posted = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Post {self.title}>'

class Category(Base):
    """
    Model representing a category for blog posts.

    Attributes:
        id (int): The unique identifier for the category.
        name (str): The name of the category.
        posts (list): A list of Post objects associated with the category.
    """
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    posts = relationship('Post', secondary='post_categories', backref='categories')

    def __repr__(self):
        return f'<Category {self.name}>'

class PostCategory(Base):
    """
    Association table for the many-to-many relationship between posts and categories.

    Attributes:
        post_id (int): The ID of the associated post.
        category_id (int): The ID of the associated category.
    """
    __tablename__ = 'post_categories'

    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), primary_key=True)