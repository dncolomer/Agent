#!/usr/bin/env python3
"""
agentctl - Command Line Interface for Agent Toolkit

This script serves as the main entry point for the Agent Toolkit,
providing a command-line interface to run, validate, and monitor
multi-agent orchestration based on configuration files.

Usage:
    agentctl run config.yaml
    agentctl validate config.yaml
    agentctl logs agent-toolkit.ndjson
    agentctl init new-config.yaml
    agentctl version
"""

import os
import sys
from pathlib import Path


def ensure_package_importable():
    """
    Ensure the agent_toolkit package is importable by adding the parent
    directory to the Python path if running from the repository.
    """
    # Get the directory containing this script
    script_dir = Path(__file__).resolve().parent
    
    # Check if we're running from the repository
    if (script_dir / "agent_toolkit").is_dir():
        # Add the parent directory to the Python path
        sys.path.insert(0, str(script_dir))
    elif (script_dir.parent / "agent_toolkit").is_dir():
        # If the script is in a bin/ directory, add the grandparent directory
        sys.path.insert(0, str(script_dir.parent))


def main():
    """Main entry point for the Agent Toolkit CLI."""
    # Ensure the package is importable
    ensure_package_importable()
    
    try:
        # Import the CLI from the agent_toolkit package
        from agent_toolkit.cli import cli
        
        # Run the CLI with the provided arguments
        cli()
    except ImportError as e:
        print(f"Error: Could not import agent_toolkit package: {e}", file=sys.stderr)
        print("Make sure the package is installed or you're running from the repository.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
