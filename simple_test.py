#!/usr/bin/env python3
"""
Simple Test Script for Agent's LLM Interface

This script demonstrates how to use the LLMInterface class to generate
a simple "Hello World" Python script.
"""

import os
import logging
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_interface import LLMInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    """Main function to test the LLM interface."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Create output directory if it doesn't exist
    output_dir = "./test_project"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the LLM interface
    logger.info("Initializing LLM interface...")
    llm = LLMInterface()
    
    # Define the file to generate
    file_path = "hello.py"
    implementation_details = "Create a simple Python script that prints 'Hello, World!' to the console"
    
    # Generate the code
    logger.info(f"Generating code for {file_path}...")
    code = llm.generate_code(
        file_path=file_path,
        implementation_details=implementation_details
    )
    
    # Save the generated code to a file
    output_path = os.path.join(output_dir, file_path)
    try:
        with open(output_path, 'w') as f:
            f.write(code)
        logger.info(f"Successfully wrote generated code to {output_path}")
        print(f"\nGenerated file: {output_path}")
        print("\nFile content:")
        print("-" * 40)
        print(code)
        print("-" * 40)
    except Exception as e:
        logger.error(f"Error writing to file: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
