#!/usr/bin/env python3
"""
Agent - Collaborative Multi-Agent Framework

This package provides a framework for creating and orchestrating collaborative 
agents that can work together to achieve complex goals. The agents are designed 
to be aware of each other and can communicate to coordinate their efforts.

Main components:
- Agent: The unified agent implementation for all agent types
- BaseAgent: Abstract base class for all agents
- EventBus: Communication system for inter-agent messaging
- Orchestrator: Manages the lifecycle and coordination of agents
"""

# Import and re-export main classes
from agent import Agent
from base_agent import BaseAgent
from events import EventBus, Event, EventType
from orchestrator import Orchestrator, run_orchestrator

# Define what's available when using `from package import *`
__all__ = [
    "Agent",
    "BaseAgent",
    "EventBus",
    "Event",
    "EventType",
    "Orchestrator",
    "run_orchestrator"
]
