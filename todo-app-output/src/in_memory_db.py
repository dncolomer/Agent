#!/usr/bin/env python3
lass InMemoryDB:
    def __init__(self):
        """
        Initializes an empty in-memory database.
        """
        self.data = {}

    def add(self, key, value):
        """
        Adds a new entry to the database.

        Parameters:
            key (str): The key for the new entry.
            value (any): The value for the new entry.

        Raises:
            ValueError: If the key already exists in the database.
        """
        if key in self.data:
            raise ValueError("Key already exists.")
        self.data[key] = value

    def update(self, key, value):
        """
        Updates an existing entry in the database.

        Parameters:
            key (str): The key for the entry to update.
            value (any): The new value for the entry.

        Raises:
            KeyError: If the key does not exist in the database.
        """
        if key not in self.data:
            raise KeyError("Key does not exist.")
        self.data[key] = value

    def delete(self, key):
        """
        Deletes an entry from the database.

        Parameters:
            key (str): The key for the entry to delete.

        Raises:
            KeyError: If the key does not exist in the database.
        """
        if key not in self.data:
            raise KeyError("Key does not exist.")
        del self.data[key]

    def get(self, key):
        """
        Retrieves the value for a given key from the database.

        Parameters:
            key (str): The key of the entry to retrieve.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key does not exist in the database.
        """
        if key not in self.data:
            raise KeyError("Key does not exist.")
        return self.data[key]

    def get_all_keys(self):
        """
        Retrieves all keys currently in the database.

        Returns:
            A list of all keys in the database.
        """
        return list(self.data.keys())