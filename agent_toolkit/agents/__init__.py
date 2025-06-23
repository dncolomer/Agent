#!/usr/bin/env python3
"""
agent_toolkit.agents - Agent Definitions for the Agent Toolkit

This package defines the different types of agents used in the Agent Toolkit:
Builder, Verifier, and Operator agents, along with a common BaseAgent.
"""

from .base_agent import BaseAgent
from .builder import BuilderAgent
# Expose the verifier agent implementation
from .verifier import VerifierAgent
# from .operator import OperatorAgent

# Define what's available when using `from agent_toolkit.agents import *`
__all__ = [
    "BaseAgent",
    "BuilderAgent",
    "VerifierAgent",
    # "OperatorAgent",
]
