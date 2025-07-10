#!/usr/bin/env python3
lass ErrorHandler:
    """
    Centralized error handling class for the TODO application.
    This class is responsible for catching exceptions and presenting user-friendly error messages.
    """

    @staticmethod
    def handle_error(error):
        """
        Static method to handle different types of errors and exceptions.
        It logs the error and returns a user-friendly message.

        Args:
            error (Exception): The exception object that was raised.

        Returns:
            str: A user-friendly error message.
        """
        # Log the actual error for debug purposes - in real scenarios, this could be written to a file or logging system
        print(f"Error: {error}")

        # Customize this section to handle specific exceptions differently
        if isinstance(error, KeyError):
            return "A KeyError has occurred. Please check if your inputs are correct."
        elif isinstance(error, ValueError):
            return "A ValueError has occurred. Please check the values provided."
        elif isinstance(error, FileNotFoundError):
            return "The file was not found. Please check the file path."
        else:
            return "An unexpected error has occurred. Please contact the support team."

# Example usage
if __name__ == "__main__":
    try:
        # Simulate an error
        raise ValueError("This is a test ValueError")
    except Exception as e:
        friendly_message = ErrorHandler.handle_error(e)
        print(friendly_message)