#!/usr/bin/env python3
"""
Agent Toolkit

A configuration-driven multi-agent orchestration system that enables building,
verifying, and operating software systems using specialized agents.

This package provides tools for defining agent configurations, orchestrating
their execution, and monitoring their progress through structured logging.
"""

__version__ = "0.1.0"

# Import main components for easy access
from agent_toolkit.orchestrator import (
    Orchestrator,
    EventBus,
    ResourceTracker,
    ConfigValidator,
    run_orchestrator,
    BaseAgent,
    BuilderAgent,
    VerifierAgent,
    OperatorAgent,
    EventType,
    Event
)

# Import CLI for command-line usage
from agent_toolkit.cli import cli

# Define what's available when using `from agent_toolkit import *`
__all__ = [
    "Orchestrator",
    "EventBus",
    "ResourceTracker",
    "ConfigValidator",
    "run_orchestrator",
    "BaseAgent",
    "BuilderAgent",
    "VerifierAgent",
    "OperatorAgent",
    "EventType",
    "Event",
    "cli",
]

# Package metadata
__author__ = "Agent Toolkit Team"
__email__ = "info@agent-toolkit.org"
__license__ = "MIT"
__copyright__ = "Copyright 2025 Agent Toolkit"
