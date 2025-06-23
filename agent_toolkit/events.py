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
    
    # Build events
    BUILD_START = "build.start"
    BUILD_STEP_START = "build.step.start"
    BUILD_STEP_COMPLETED = "build.step.completed"
    BUILD_STEP_FAILED = "build.step.failed"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"
    
    # Verification events
    VERIFY_START = "verify.start"
    VERIFY_TEST_START = "verify.test.start"
    VERIFY_TEST_PASSED = "verify.test.passed"
    VERIFY_TEST_FAILED = "verify.test.failed"
    VERIFY_COMPLETED = "verify.completed"
    VERIFY_FAILED = "verify.failed"
    
    # Operation events
    OPERATE_START = "operate.start"
    OPERATE_ACTION = "operate.action"
    OPERATE_ALERT = "operate.alert"
    OPERATE_COMPLETED = "operate.completed"
    OPERATE_FAILED = "operate.failed"
    
    # Resource events
    RESOURCE_LIMIT_WARNING = "resource.limit.warning"
    RESOURCE_LIMIT_EXCEEDED = "resource.limit.exceeded"


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
        self._MAX_HISTORY = 10_000  # override via env if desired
        
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
        """
        summary: Dict[str, int] = {}
        for ev in self.history:
            summary[ev.type] = summary.get(ev.type, 0) + 1
        return {
            "total_events": len(self.history),
            "by_type": summary
        }

    async def process_events(self):
        """Process events from the queue."""
        while True:
            event = await self.queue.get()
            
            # Call subscribers for this event type
            if event.type in self.subscribers:
                for callback in self.subscribers[event.type]:
                    try:
                        await callback(event)
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
