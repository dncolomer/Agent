#!/usr/bin/env python3
# Utility script to process and manage inline code comments

def extract_comments_from_code(code):
    """
    Extracts inline comments from the given code.

    Args:
    code (str): The code containing inline comments.

    Returns:
    list: A list of extracted inline comments.
    """
    comments = []
    lines = code.split('\n')
    for line in lines:
        line = line.strip()
        if '#' in line:
            comment = line.split('#', 1)[1].strip()
            comments.append(comment)
    return comments

def count_comments(comments):
    """
    Counts the number of comments in the given list of comments.

    Args:
    comments (list): A list of comments.

    Returns:
    int: The total number of comments.
    """
    return len(comments)

def remove_comments_from_code(code):
    """
    Removes inline comments from the given code.

    Args:
    code (str): The code containing inline comments.

    Returns:
    str: The code with inline comments removed.
    """
    lines = code.split('\n')
    code_without_comments = []
    for line in lines:
        line = line.strip()
        if '#' in line:
            line = line.split('#', 1)[0].strip()
        code_without_comments.append(line)
    return '\n'.join(code_without_comments)