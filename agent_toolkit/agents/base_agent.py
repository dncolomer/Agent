#!/usr/bin/env python3
"""
BaseAgent - Abstract Base Class for Agent Toolkit Agents

This module defines the BaseAgent, an abstract base class that serves as a
foundation for all agent types within the Agent Toolkit. It provides common
functionalities and defines the interface that concrete agent implementations
must adhere to.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Event primitives are now defined in a dedicated module to avoid circular imports.
from agent_toolkit.events import EventBus, Event, EventType


class BaseAgent(ABC):
    """
    BaseAgent class serves as an abstract foundation for all agent types.
    It provides common functionalities like initialization, logging, and event publishing,
    and defines the interface that all concrete agents must implement.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any], event_bus: EventBus, logger: logging.Logger):
        """
        Initializes the BaseAgent.

        Args:
            agent_id: A unique identifier for the agent instance.
            config: The configuration dictionary for the agent.
            event_bus: An instance of the EventBus for inter-agent communication.
            logger: A logger instance for the agent.
        """
        self.agent_id = agent_id
        self.config = config
        self.event_bus = event_bus
        self.logger = logger
        # Assuming run_id is passed in the config dictionary by the Orchestrator
        self.run_id = config.get("run_id", "unknown_run")

        self.logger.info(f"Agent {self.agent_id} initialized.")

        # ------------------------------------------------------------------ #
        # Collaboration & Messaging setup                                    #
        # ------------------------------------------------------------------ #
        # Classify agent role (builder / verifier / operator) if provided
        self.agent_type: str = config.get("agent_type", "generic")

        # Subscribe for direct messages routed through the EventBus
        self.event_bus.subscribe(EventType.AGENT_MESSAGE, self._handle_agent_message)

    @abstractmethod
    async def start(self):
        """
        Abstract method to start the agent's execution.
        Concrete agent implementations must override this method.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Abstract method to stop the agent's execution and clean up resources.
        Concrete agent implementations must override this method.
        """
        pass

    async def publish_event(self, event_type: EventType, payload: Optional[Dict[str, Any]] = None):
        """
        Publishes an event to the event bus.

        Args:
            event_type: The type of event to publish.
            payload: Optional dictionary containing event-specific data.
        """
        if payload is None:
            payload = {}
        event = Event(type=event_type, agent_id=self.agent_id, run_id=self.run_id, payload=payload)
        await self.event_bus.publish(event)
        self.logger.debug(f"Agent {self.agent_id} published event: {event_type.value}")

    # ------------------------------------------------------------------ #
    # Shared Context Helpers                                             #
    # ------------------------------------------------------------------ #
    def set_context(self, key: str, value: Any):
        """Publish a value into the shared context store accessible to all agents."""
        self.event_bus.set_context(key, value)

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the shared context."""
        return self.event_bus.get_context(key, default)

    # ------------------------------------------------------------------ #
    # Direct Messaging Helpers                                           #
    # ------------------------------------------------------------------ #
    async def send_message(self, to_agent: str, payload: Dict[str, Any]):
        """
        Send a direct message to another agent.  The EventBus will route the
        message as an `AGENT_MESSAGE` event whose payload includes `to`.
        """
        await self.event_bus.send_message(
            to_agent=to_agent,
            run_id=self.run_id,
            payload={**payload, "from": self.agent_id}
        )

    async def _handle_agent_message(self, event: Event):
        """
        Default message handler.  Subclasses can override to implement
        richer behaviours.  This basic implementation simply logs the
        message if it is addressed to this agent.
        """
        target = event.payload.get("to")
        if target not in (self.agent_id, "*"):
            # Not for us
            return
        self.logger.debug(
            f"Agent {self.agent_id} received message from {event.payload.get('from')}: "
            f"{event.payload.get('body')}"
        )

    # ------------------------------------------------------------------ #
    # Event History helper                                               #
    # ------------------------------------------------------------------ #
    def query_events(
        self,
        *,
        event_type: Optional[EventType] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ):
        """Convenience wrapper around EventBus.query_events filtered for this agent."""
        return self.event_bus.query_events(
            agent_id=self.agent_id,
            event_type=event_type,
            since=since,
            until=until,
        )
