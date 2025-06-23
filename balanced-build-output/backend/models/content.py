#!/usr/bin/env python3
"""
Data models for content entities.

This module defines the database models for various types of content
managed by the application, including blog posts, pages, media, etc.
It also handles relationships between different content types.
"""

from datetime import datetime
from backend import db


class BlogPost(db.Model):
    """
    Model representing a blog post.

    Attributes:
        id (int): The unique identifier for the blog post.
        title (str): The title of the blog post.
        content (str): The content body of the blog post.
        author_id (int): The ID of the user who authored the post.
        created_at (datetime): The timestamp when the post was created.
        updated_at (datetime): The timestamp when the post was last updated.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('blog_posts', lazy='dynamic'))

    def __repr__(self):
        return f'<BlogPost "{self.title}">'


class Page(db.Model):
    """
    Model representing a static page.

    Attributes:
        id (int): The unique identifier for the page.
        title (str): The title of the page.
        content (str): The content body of the page.
        slug (str): The URL slug for the page.
        created_at (datetime): The timestamp when the page was created.
        updated_at (datetime): The timestamp when the page was last updated.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Page "{self.title}">'


class Media(db.Model):
    """
    Model representing a media file (image, video, etc.).

    Attributes:
        id (int): The unique identifier for the media file.
        filename (str): The name of the media file.
        filetype (str): The type of the media file (e.g., 'image/jpeg', 'video/mp4').
        created_at (datetime): The timestamp when the media file was uploaded.
    """

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Media "{self.filename}">'