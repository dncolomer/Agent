#!/usr/bin/env python3
import sys

class TodoApp:
    def __init__(self):
        """Initialize the Todo application with an empty task list."""
        self.tasks = []

    def add_task(self, task):
        """Add a new task to the list."""
        self.tasks.append(task)
        print(f"Task added: {task}")

    def list_tasks(self):
        """Print all tasks in the list."""
        if not self.tasks:
            print("No tasks to show.")
        else:
            for i, task in enumerate(self.tasks, start=1):
                print(f"{i}. {task}")

    def remove_task(self, task_number):
        """Remove a task from the list by its number."""
        try:
            if task_number < 1 or task_number > len(self.tasks):
                print("Invalid task number.")
                return
            removed_task = self.tasks.pop(task_number - 1)
            print(f"Task removed: {removed_task}")
        except ValueError:
            print("Please provide a valid task number.")

def main():
    app = TodoApp()

    while True:
        print("\nTODO Application")
        print("1. Add a task")
        print("2. List all tasks")
        print("3. Remove a task")
        print("4. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            task = input("Enter the task description: ")
            app.add_task(task)
        elif choice == '2':
            app.list_tasks()
        elif choice == '3':
            try:
                task_number = int(input("Enter the task number to remove: "))
                app.remove_task(task_number)
            except ValueError:
                print("Please enter a valid number.")
        elif choice == '4':
            print("Exiting the application.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication closed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)