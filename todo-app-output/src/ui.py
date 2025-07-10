#!/usr/bin/env python3
lass TodoUI:
    def __init__(self, todo_service):
        """
        Initializes the TodoUI class with a todo_service.

        :param todo_service: The service handling the business logic for TODO operations.
        """
        self.todo_service = todo_service

    def display_menu(self):
        """
        Displays the main menu options to the user.
        """
        print("\nTODO Application")
        print("----------------")
        print("1. List all TODOs")
        print("2. Add a new TODO")
        print("3. Complete a TODO")
        print("4. Delete a TODO")
        print("5. Exit")

    def list_todos(self):
        """
        Fetches and displays all TODO items.
        """
        todos = self.todo_service.get_all_todos()
        if todos:
            print("\nTODOs:")
            for idx, todo in enumerate(todos, start=1):
                status = "Done" if todo['completed'] else "Pending"
                print(f"{idx}. {todo['title']} - {status}")
        else:
            print("\nNo TODOs found!")

    def add_todo(self):
        """
        Captures user input to add a new TODO item.
        """
        title = input("Enter the title of the TODO: ").strip()
        if title:
            self.todo_service.add_todo(title)
            print("TODO added successfully!")
        else:
            print("Invalid input. Title cannot be empty.")

    def complete_todo(self):
        """
        Marks a TODO item as completed based on user input.
        """
        try:
            todo_id = int(input("Enter the TODO ID to mark as completed: "))
            if self.todo_service.complete_todo(todo_id):
                print("TODO marked as completed.")
            else:
                print("TODO not found.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    def delete_todo(self):
        """
        Deletes a TODO item based on user input.
        """
        try:
            todo_id = int(input("Enter the TODO ID to delete: "))
            if self.todo_service.delete_todo(todo_id):
                print("TODO deleted successfully.")
            else:
                print("TODO not found.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    def run(self):
        """
        Starts the user interface loop, processing user inputs.
        """
        while True:
            self.display_menu()
            choice = input("Enter your choice: ")

            if choice == '1':
                self.list_todos()
            elif choice == '2':
                self.add_todo()
            elif choice == '3':
                self.complete_todo()
            elif choice == '4':
                self.delete_todo()
            elif choice == '5':
                print("Exiting the application...")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")