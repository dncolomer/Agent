#!/usr/bin/env python3
"""
Agent - Main Entry Point

This module serves as the main entry point for the Agent package,
allowing it to be executed directly with `python -m __main__`.
"""

import sys
from orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
