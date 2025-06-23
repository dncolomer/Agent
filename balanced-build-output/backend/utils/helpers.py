#!/usr/bin/env python3
def add_numbers(num1, num2):
    """
    This function takes two numbers as input and returns the sum of the numbers.

    Args:
    num1 (int): The first number
    num2 (int): The second number

    Returns:
    int: The sum of num1 and num2
    """
    try:
        result = num1 + num2
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def subtract_numbers(num1, num2):
    """
    This function takes two numbers as input and returns the difference of the numbers.

    Args:
    num1 (int): The first number
    num2 (int): The second number

    Returns:
    int: The difference of num1 and num2
    """
    try:
        result = num1 - num2
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        return None