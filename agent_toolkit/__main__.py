#!/usr/bin/env python3
"""
Agent Toolkit - Main Entry Point

This module serves as the main entry point for the agent_toolkit package,
allowing it to be executed directly with `python -m agent_toolkit`.
"""

import sys
from agent_toolkit.orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
