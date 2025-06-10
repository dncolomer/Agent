#!/usr/bin/env python3
"""
Agent - Main Entry Point

This module serves as the main entry point for the Agent application.
It handles command-line arguments and initializes the core components.
"""

import argparse
import logging
import sys
import os
from typing import List, Optional
from dotenv import load_dotenv

from agent import Agent
from config import load_config, get_config


def setup_logging(verbose: bool = False) -> None:
    """Configure the logging system.

    Args:
        verbose: If True, set logging level to DEBUG, otherwise INFO
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Agent - A tool for automating coding projects"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "-d", "--directory", 
        default="./project", 
        help="Directory where the project will be developed"
    )
    parser.add_argument(
        "-p", "--prompt", 
        help="Description of what you want to build"
    )
    parser.add_argument(
        "--plan-file", 
        default="development_plan.md", 
        help="Filename for the development plan"
    )
    parser.add_argument(
        "--config", 
        help="Path to a configuration file (JSON or INI format)"
    )
    parser.add_argument(
        "--model", 
        help="OpenRouter model to use (e.g., openai/gpt-4-turbo-preview, anthropic/claude-3-opus)"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to environment file (.env)"
    )
    
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the application.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed_args = parse_args(args)
    
    # Load environment variables from .env file
    if os.path.exists(parsed_args.env_file):
        load_dotenv(parsed_args.env_file)
        print(f"Loaded environment variables from {parsed_args.env_file}")
    else:
        load_dotenv()  # Try default locations
        
    setup_logging(parsed_args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("Starting Agent application")

    try:
        # Load configuration if specified
        if parsed_args.config:
            if not os.path.exists(parsed_args.config):
                logger.error(f"Configuration file not found: {parsed_args.config}")
                return 1
            
            success = load_config(parsed_args.config)
            if not success:
                logger.error(f"Failed to load configuration from: {parsed_args.config}")
                return 1
            
            logger.info(f"Loaded configuration from: {parsed_args.config}")
        
        # Get absolute path for project directory
        project_dir = os.path.abspath(parsed_args.directory)
        
        # Initialize the agent with optional model parameter
        agent_kwargs = {
            "project_dir": project_dir,
            "plan_file": parsed_args.plan_file
        }
        
        # Add model if specified
        if parsed_args.model:
            agent_kwargs["model_name"] = parsed_args.model
            
        agent = Agent(**agent_kwargs)
        logger.info(f"Agent initialized with project directory: {project_dir}")
        
        # If a prompt was provided, run the agent
        if parsed_args.prompt:
            success = agent.run(parsed_args.prompt)
            if success:
                logger.info("Project development completed successfully")
                print("\nProject development completed! Please test the implementation.")
                print(f"Project files are located in: {project_dir}")
            else:
                logger.error("Project development failed")
                return 1
        else:
            logger.info("No prompt provided. Use --prompt to specify what to build.")
            print("Please provide a prompt describing what you want to build using the --prompt option.")
            
        return 0
    except Exception as e:
        logger.exception(f"Error running Agent: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
