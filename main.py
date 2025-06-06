#!/usr/bin/env python3
"""
Agent - Main Entry Point

This module serves as the main entry point for the Agent application.
It handles command-line arguments and initializes the core components.
"""

import argparse
import logging
import sys
from typing import List, Optional


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
        description="Agent - A tool for automating tasks"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    # Add more command-line arguments as needed
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the application.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed_args = parse_args(args)
    setup_logging(parsed_args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("Starting Agent application")

    try:
        # TODO: Initialize and run the main application logic
        logger.info("Agent initialized successfully")
        return 0
    except Exception as e:
        logger.exception(f"Error running Agent: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
