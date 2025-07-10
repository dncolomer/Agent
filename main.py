#!/usr/bin/env python3
"""
Agent - Main Entry Point (Compatibility Wrapper)

This module serves as a compatibility wrapper that delegates to the agent_toolkit
implementation. It maintains backward compatibility with existing scripts while
using the new modular architecture.
"""

import sys
# The orchestration entry-point lives in orchestrator.py at the
# repository root after the project flattening.  Import its `main`
# function directly.
from orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
