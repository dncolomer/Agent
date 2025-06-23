#!/usr/bin/env python3
import re

def validate_email(email):
    """
    Validate the format of an email address.

    Args:
        email (str): The email address to validate.

    Returns:
        bool: True if the email address is valid, False otherwise.
    """
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_password(password):
    """
    Validate the strength of a password.

    Args:
        password (str): The password to validate.

    Returns:
        bool: True if the password meets the minimum strength requirements, False otherwise.
    """
    # Password must be at least 8 characters long
    if len(password) < 8:
        return False

    # Password must contain at least one uppercase letter, one lowercase letter, and one digit
    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)
    has_digit = any(char.isdigit() for char in password)

    return has_upper and has_lower and has_digit

def validate_username(username):
    """
    Validate the format of a username.

    Args:
        username (str): The username to validate.

    Returns:
        bool: True if the username is valid, False otherwise.
    """
    # Username must be between 4 and 20 characters long
    if not 4 <= len(username) <= 20:
        return False

    # Username must start with a letter
    if not username[0].isalpha():
        return False

    # Username can only contain alphanumeric characters and underscores
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))

def validate_url(url):
    """
    Validate the format of a URL.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+$'
    return bool(re.match(pattern, url))