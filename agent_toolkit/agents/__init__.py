#!/usr/bin/env python3
"""
agent_toolkit.agents - Agent Definitions for the Agent Toolkit

This package exposes the unified `Agent` implementation together with the
shared `BaseAgent` class.  Specific roles such as *builder* and *operator*
are now expressed via the agent configuration (the `type` field) rather than
dedicated Python subclasses.
"""

from .base import BaseAgent
from .agent import Agent

# Define what's available when using `from agent_toolkit.agents import *`
__all__ = [
    "BaseAgent",
    "Agent",
]
