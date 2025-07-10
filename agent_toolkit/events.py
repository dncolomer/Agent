#!/usr/bin/env python3
"""
agent_toolkit.events - Event Definitions and Event Bus for the Agent Toolkit

This module defines the EventType enum, Event model, and EventBus class.
It is designed to centralize event-related components and break circular
dependencies between other modules like orchestrator.py and base_agent.py.
"""

import asyncio
import datetime
import logging
from enum import Enum
from typing import Any, Dict, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types for the event bus."""
    # System events
    SYSTEM_START = "system.start"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_LOADED = "config.loaded"
    CONFIG_VALIDATED = "config.validated"
    
    # Unified agent-centric events
    AGENT_START = "agent.start"
    AGENT_TASK_START = "agent.task.start"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    AGENT_TASK_FAILED = "agent.task.failed"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    
    # Resource events
    RESOURCE_LIMIT_WARNING = "resource.limit.warning"
    RESOURCE_LIMIT_EXCEEDED = "resource.limit.exceeded"

    # Direct agent-to-agent messaging (payload should contain
    # ``to`` and optional ``reply_to`` identifiers)
    AGENT_MESSAGE = "agent.message"


class Event(BaseModel):
    """Event model for the event bus."""
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    agent_id: Optional[str] = None
    run_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventBus:
    """
    Simple in-process event bus for agent communication.
    
    This class provides a publish-subscribe mechanism for agents to communicate
    with each other and with the orchestration engine.
    """
    
    def __init__(self, logger: logging.Logger):
        self.subscribers: Dict[EventType, Set[callable]] = {}
        self.queue = asyncio.Queue()
        self.logger = logger
        # Keep a history of all events for debugging / inspection.
        # Unbounded by default; could be capped by MAX_HISTORY for memory safety.
        self.history: list[Event] = []
        # Track how long each subscriber spends processing an event so we
        # can later produce consumption metrics and identify slow handlers.
        # Each entry: {"event": EventType, "agent": str, "ms": float}
        self.consumption_records: list[Dict[str, Any]] = []
        self._MAX_HISTORY = 10_000  # override via env if desired

        # Shared, in-memory context store that agents can use to broadcast
        # small pieces of state (design decisions, partial plans, etc.).
        # For real production you might back this with a DB or redis.
        self.shared_context: Dict[str, Any] = {}
        
    def subscribe(self, event_type: EventType, callback: callable):
        """Subscribe to an event type with a callback function."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(callback)
        
    def unsubscribe(self, event_type: EventType, callback: callable):
        """Unsubscribe from an event type."""
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        self.logger.debug(f"Event published: {event.type}", extra={"event": event.dict()})

        # ------------------------------------------------------------------ #
        # Debugging / history tracking                                        #
        # ------------------------------------------------------------------ #
        # Record event in history (trim oldest if we exceed capacity).
        self.history.append(event)
        if len(self.history) > self._MAX_HISTORY:
            self.history.pop(0)

        await self.queue.put(event)
        
    # ------------------------------------------------------------------ #
    # Convenience helpers                                                #
    # ------------------------------------------------------------------ #

    # Shared context ---------------------------------------------------- #
    def set_context(self, key: str, value: Any):
        """Publish a value into the shared context store."""
        self.shared_context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the shared context."""
        return self.shared_context.get(key, default)

    # Direct messaging --------------------------------------------------- #
    async def send_message(self, to_agent: str, run_id: str, payload: Dict[str, Any]):
        """
        Send a direct message to another agent.  Internally this is just a
        normal event with type ``AGENT_MESSAGE`` that includes the recipient.
        """
        await self.publish(Event(
            type=EventType.AGENT_MESSAGE,
            run_id=run_id,
            payload={**payload, "to": to_agent}
        ))

    async def publish_info(self, event_type: EventType, run_id: str, payload: Optional[Dict[str, Any]] = None):
        """Helper to publish an informational event quickly."""
        await self.publish(Event(type=event_type, run_id=run_id, payload=payload or {}))

    async def publish_debug(self, msg: str, run_id: str, agent_id: Optional[str] = None):
        """Publish a debug string as an event (type SYSTEM_START used generically)."""
        await self.publish(Event(
            type=EventType.CONFIG_LOADED,
            run_id=run_id,
            agent_id=agent_id,
            payload={"debug": msg}
        ))

    # ------------------------------------------------------------------ #
    # History & summary utilities                                        #
    # ------------------------------------------------------------------ #
    def get_history(self, limit: Optional[int] = None) -> list[Event]:
        """
        Retrieve the most recent `limit` events (or all if limit is None).
        Returned list is in chronological order (oldest -> newest).
        """
        if limit is None or limit >= len(self.history):
            return list(self.history)
        return self.history[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a simple summary containing:
          - total event count
          - count per EventType
          - basic consumption stats
        """
        summary: Dict[str, int] = {}
        for ev in self.history:
            summary[ev.type] = summary.get(ev.type, 0) + 1
        # Consumption
        cons_summary: Dict[str, Dict[str, Any]] = {}
        for rec in self.consumption_records:
            agent = rec["agent"] or "unknown"
            etype = rec["event"].value
            aggr = cons_summary.setdefault(agent, {}).setdefault(etype, {"count": 0, "total_ms": 0.0})
            aggr["count"] += 1
            aggr["total_ms"] += rec["ms"]
        return {
            "total_events": len(self.history),
            "by_type": summary,
            "consumption": cons_summary,
        }

    # Query helper ------------------------------------------------------- #
    def query_events(
        self,
        *,
        agent_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> list[Event]:
        """
        Retrieve events filtered by optional agent, type and ISO-timestamp
        range.  Useful for debugging or producing custom reports.
        """
        def _in_range(ev_ts: str) -> bool:
            return ((since is None or ev_ts >= since) and
                    (until is None or ev_ts <= until))

        return [
            ev for ev in self.history
            if (agent_id is None or ev.agent_id == agent_id)
            and (event_type is None or ev.type == event_type)
            and _in_range(ev.timestamp)
        ]

    async def process_events(self):
        """Process events from the queue."""
        while True:
            event = await self.queue.get()
            
            # Call subscribers for this event type
            if event.type in self.subscribers:
                for callback in self.subscribers[event.type]:
                    try:
                        start = datetime.datetime.now().timestamp()
                        await callback(event)
                        elapsed = (datetime.datetime.now().timestamp() - start) * 1000.0

                        # Attempt to identify agent if callback is a bound method
                        agent = None
                        if hasattr(callback, "__self__") and callback.__self__ is not None:
                            agent = getattr(callback.__self__, "agent_id", None)

                        self.consumption_records.append(
                            {"event": event.type, "agent": agent, "ms": elapsed}
                        )
                        # Trim for memory
                        if len(self.consumption_records) > self._MAX_HISTORY:
                            self.consumption_records.pop(0)
                    except Exception as e:
                        self.logger.error(f"Error in event subscriber: {e}", 
                                         extra={"event_type": event.type, "error": str(e)})
            
            # Mark task as done
            self.queue.task_done()
            
            # Special handling for shutdown event
            if event.type == EventType.SYSTEM_SHUTDOWN:
                # Wait for any remaining events to be processed
                if self.queue.empty():
                    break
