#!/usr/bin/env python3
from typing import List, Optional

from backend.models import Content, db


class ContentRepository:
    """
    Data access layer for interacting with the database and persisting content data.
    """

    @staticmethod
    def create(content: Content) -> Content:
        """
        Create a new content entry in the database.

        Args:
            content (Content): The content object to be created.

        Returns:
            Content: The created content object.
        """
        db.session.add(content)
        db.session.commit()
        return content

    @staticmethod
    def get_by_id(content_id: int) -> Optional[Content]:
        """
        Retrieve a content object from the database by its ID.

        Args:
            content_id (int): The ID of the content object.

        Returns:
            Optional[Content]: The content object, or None if not found.
        """
        return Content.query.get(content_id)

    @staticmethod
    def get_all() -> List[Content]:
        """
        Retrieve all content objects from the database.

        Returns:
            List[Content]: A list of all content objects.
        """
        return Content.query.all()

    @staticmethod
    def update(content: Content) -> Content:
        """
        Update an existing content object in the database.

        Args:
            content (Content): The updated content object.

        Returns:
            Content: The updated content object.
        """
        db.session.merge(content)
        db.session.commit()
        return content

    @staticmethod
    def delete(content: Content) -> None:
        """
        Delete a content object from the database.

        Args:
            content (Content): The content object to be deleted.
        """
        db.session.delete(content)
        db.session.commit()