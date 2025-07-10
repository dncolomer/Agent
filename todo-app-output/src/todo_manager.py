#!/usr/bin/env python3
lass TodoManager:
    def __init__(self):
        """Initialize the TodoManager with an empty list of TODOs."""
        self.todos = []

    def add_todo(self, todo):
        """Add a new TODO item to the list.
        
        Args:
            todo (str): The TODO item to be added.
        """
        if not todo:
            raise ValueError("TODO item cannot be empty.")
        self.todos.append(todo)

    def remove_todo(self, index):
        """Remove a TODO item from the list by its index.
        
        Args:
            index (int): The index of the TODO item to be removed.
        
        Raises:
            IndexError: If the index is out of bounds.
        """
        if index < 0 or index >= len(self.todos):
            raise IndexError("TODO item index out of bounds.")
        del self.todos[index]

    def get_todos(self):
        """Return the list of TODO items.
        
        Returns:
            list: The current list of TODO items.
        """
        return self.todos

    def update_todo(self, index, new_todo):
        """Update a TODO item in the list by its index.
        
        Args:
            index (int): The index of the TODO item to be updated.
            new_todo (str): The new value for the TODO item.
        
        Raises:
            IndexError: If the index is out of bounds.
        """
        if index < 0 or index >= len(self.todos):
            raise IndexError("TODO item index out of bounds.")
        if not new_todo:
            raise ValueError("TODO item cannot be empty.")
        self.todos[index] = new_todo

    def clear_todos(self):
        """Clear all TODO items from the list."""
        self.todos.clear()

if __name__ == "__main__":
    manager = TodoManager()
    # Example usage
    try:
        manager.add_todo("Learn Python")
        manager.add_todo("Read documentation")
        print("Current TODOs:", manager.get_todos())
        manager.update_todo(0, "Learn Python - Completed")
        print("Updated TODOs:", manager.get_todos())
        manager.remove_todo(1)
        print("After removal:", manager.get_todos())
        manager.clear_todos()
        print("After clearing:", manager.get_todos())
    except (ValueError, IndexError) as error:
        print(f"Error: {error}")