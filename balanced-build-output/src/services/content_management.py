#!/usr/bin/env python3
"""Core business logic and services for managing content, including CRUD operations, access control, and content versioning."""

import datetime

class ContentManager:
    """
    Manages content creation, retrieval, updating, and deletion (CRUD operations),
    as well as access control and content versioning.
    """

    def __init__(self, database):
        """
        Initialize the ContentManager with a database connection.

        Args:
            database (object): A database connection object.
        """
        self.db = database

    def create_content(self, title, body, author, access_level):
        """
        Create a new content item in the database.

        Args:
            title (str): The title of the content.
            body (str): The body or content of the item.
            author (str): The author or creator of the content.
            access_level (str): The access level for the content (e.g., 'public', 'private').

        Returns:
            int: The ID of the newly created content item.
        """
        now = datetime.datetime.now()
        query = "INSERT INTO content (title, body, author, access_level, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (title, body, author, access_level, now, now)
        cursor = self.db.cursor()
        cursor.execute(query, values)
        content_id = cursor.lastrowid
        self.db.commit()
        cursor.close()
        return content_id

    def get_content(self, content_id, user_id):
        """
        Retrieve a content item from the database.

        Args:
            content_id (int): The ID of the content item to retrieve.
            user_id (int): The ID of the user requesting the content.

        Returns:
            dict: A dictionary containing the content item data if access is allowed, otherwise None.
        """
        query = "SELECT title, body, author, access_level FROM content WHERE id = %s"
        cursor = self.db.cursor()
        cursor.execute(query, (content_id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            title, body, author, access_level = result
            if access_level == 'public' or (access_level == 'private' and author == user_id):
                return {
                    'title': title,
                    'body': body,
                    'author': author,
                    'access_level': access_level
                }

        return None

    def update_content(self, content_id, title, body, author, access_level):
        """
        Update an existing content item in the database.

        Args:
            content_id (int): The ID of the content item to update.
            title (str): The new title for the content.
            body (str): The new body or content.
            author (str): The author or creator of the content.
            access_level (str): The new access level for the content (e.g., 'public', 'private').

        Returns:
            bool: True if the content item was updated successfully, False otherwise.
        """
        now = datetime.datetime.now()
        query = "UPDATE content SET title = %s, body = %s, author = %s, access_level = %s, updated_at = %s WHERE id = %s"
        values = (title, body, author, access_level, now, content_id)
        cursor = self.db.cursor()
        cursor.execute(query, values)
        rows_affected = cursor.rowcount
        self.db.commit()
        cursor.close()
        return rows_affected > 0

    def delete_content(self, content_id):
        """
        Delete a content item from the database.

        Args:
            content_id (int): The ID of the content item to delete.

        Returns:
            bool: True if the content item was deleted successfully, False otherwise.
        """
        query = "DELETE FROM content WHERE id = %s"
        cursor = self.db.cursor()
        cursor.execute(query, (content_id,))
        rows_affected = cursor.rowcount
        self.db.commit()
        cursor.close()
        return rows_affected > 0

    def get_content_history(self, content_id):
        """
        Retrieve the version history of a content item.

        Args:
            content_id (int): The ID of the content item to retrieve the history for.

        Returns:
            list: A list of dictionaries, each representing a version of the content item.
        """
        query = "SELECT title, body, author, access_level, created_at, updated_at FROM content_history WHERE content_id = %s ORDER BY updated_at DESC"
        cursor = self.db.cursor()
        cursor.execute(query, (content_id,))
        results = cursor.fetchall()
        cursor.close()

        history = []
        for result in results:
            title, body, author, access_level, created_at, updated_at = result
            history.append({
                'title': title,
                'body': body,
                'author': author,
                'access_level': access_level,
                'created_at': created_at,
                'updated_at': updated_at
            })

        return history