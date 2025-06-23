#!/usr/bin/env python3
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.sql import func

# Base class for declarative class definitions
Base = declarative_base()

# User model representing a user in the system
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to the Content model
    contents = relationship('Content', back_populates='author')

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

# Content model representing content created by users
class Content(Base):
    __tablename__ = 'contents'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Relationship to the User model
    author = relationship('User', back_populates='contents')

    def __repr__(self):
        return f"<Content(title='{self.title}', author_id='{self.author_id}')>"

# Function to initialize the database
def init_db(uri):
    engine = create_engine(uri)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

# Example usage:
# Session = init_db('sqlite:///example.db')
# session = Session()
# new_user = User(username='johndoe', email='john@example.com', password_hash='hashed_password')
# session.add(new_user)
# session.commit()