#!/usr/bin/env python3
"""
User Service module

This module handles user authentication, authorization, and user-related operations.
"""

import bcrypt
from flask import session
from models import User, Role
from database import db_session
from exceptions import (
    UserNotFoundError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UnauthorizedAccessError,
)


def authenticate_user(email, password):
    """
    Authenticate a user with the provided email and password.

    Args:
        email (str): The user's email address.
        password (str): The user's password.

    Returns:
        User: The authenticated user object.

    Raises:
        UserNotFoundError: If the user with the provided email is not found.
        InvalidCredentialsError: If the provided password is incorrect.
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        raise UserNotFoundError(f"User with email {email} not found.")

    if not bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
        raise InvalidCredentialsError("Invalid credentials.")

    return user


def register_user(name, email, password, role_id):
    """
    Register a new user with the provided details.

    Args:
        name (str): The user's name.
        email (str): The user's email address.
        password (str): The user's password.
        role_id (int): The ID of the user's role.

    Returns:
        User: The newly registered user object.

    Raises:
        UserAlreadyExistsError: If a user with the provided email already exists.
    """
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        raise UserAlreadyExistsError(f"User with email {email} already exists.")

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    role = Role.query.get(role_id)
    user = User(name=name, email=email, password=hashed_password.decode("utf-8"), role=role)
    db_session.add(user)
    db_session.commit()
    return user


def authorize_user(user_id, required_role):
    """
    Authorize a user for a specific role.

    Args:
        user_id (int): The ID of the user to authorize.
        required_role (str): The required role for authorization.

    Returns:
        bool: True if the user is authorized, False otherwise.

    Raises:
        UserNotFoundError: If the user with the provided ID is not found.
        UnauthorizedAccessError: If the user does not have the required role.
    """
    user = User.query.get(user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")

    if user.role.name != required_role:
        raise UnauthorizedAccessError(f"User does not have the required role: {required_role}")

    return True


def get_user_by_id(user_id):
    """
    Get a user by their ID.

    Args:
        user_id (int): The ID of the user to retrieve.

    Returns:
        User: The user object.

    Raises:
        UserNotFoundError: If the user with the provided ID is not found.
    """
    user = User.query.get(user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")
    return user


def login_user(user):
    """
    Log in a user by storing their ID in the session.

    Args:
        user (User): The user object to log in.
    """
    session["user_id"] = user.id


def logout_user():
    """
    Log out the currently logged-in user by removing their ID from the session.
    """
    session.pop("user_id", None)


def get_current_user():
    """
    Get the currently logged-in user.

    Returns:
        User: The user object if a user is logged in, None otherwise.
    """
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None