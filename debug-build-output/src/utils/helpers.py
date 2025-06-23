#!/usr/bin/env python3
# src/utils/helpers.py

"""
Utility functions for common tasks and data processing
"""

def add_numbers(num1, num2):
    """
    Add two numbers together and return the result.

    Parameters:
    num1 (int): The first number
    num2 (int): The second number

    Returns:
    int: The sum of num1 and num2
    """
    try:
        result = num1 + num2
        return result
    except TypeError:
        print("Error: Please provide valid numbers for addition.")
        return None

def multiply_numbers(num1, num2):
    """
    Multiply two numbers and return the result.

    Parameters:
    num1 (int): The first number
    num2 (int): The second number

    Returns:
    int: The product of num1 and num2
    """
    try:
        result = num1 * num2
        return result
    except TypeError:
        print("Error: Please provide valid numbers for multiplication.")
        return None

def check_prime(number):
    """
    Check if a number is a prime number.

    Parameters:
    number (int): The number to check

    Returns:
    bool: True if the number is prime, False otherwise
    """
    if number <= 1:
        return False
    for i in range(2, int(number**0.5) + 1):
        if number % i == 0:
            return False
    return True