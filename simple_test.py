#!/usr/bin/env python3
"""
Simple Test Script for Agent's LLM Interface

This script demonstrates how to use the LLMInterface class to test connectivity
with OpenRouter and generate a simple text response.
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
    
    # Initialize the LLM interface
    logger.info("Initializing LLM interface...")
    llm = LLMInterface()
    
    # Check if API key is available
    if not llm.api_key:
        logger.error("OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file.")
        print("\nERROR: OpenRouter API key is missing. Please check your .env file.")
        return 1

    # Define a simple prompt
    test_prompt = "What is the capital of France?"
    
    print(f"\n--- Testing LLM Interface ---")
    print(f"Prompt: {test_prompt}")
    print(f"Using model: {llm.model_name}")
    
    try:
        # Try to generate a simple response
        logger.info("Generating simple response from LLM...")
        response = llm.generate_text(prompt=test_prompt, max_tokens=50)
        
        print(f"\nResponse:\n{response}")
        logger.info("LLM interface test completed successfully.")
        return 0
        
    except Exception as e:
        logger.exception(f"Error during LLM interface test: {e}")
        print(f"\nERROR: Failed to get response from LLM. Details: {e}")
        print("Please check your internet connection, OpenRouter API key, and model name.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
