#!/usr/bin/env python3
"""
Base Agent Class for Agent Toolkit

This module provides the BaseAgent abstract base class that all specific
agent types (Builder, Verifier, Operator) inherit from. It handles common
functionality like initialization, communication, and lifecycle management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from agent_toolkit.events import EventBus, Event, EventType


class BaseAgent(ABC):
    """
    Abstract base class for all agent types.
    
    This class provides common functionality for initialization, communication,
    and lifecycle management. Specific agent types should inherit from this
    class and implement the abstract methods.
    """
    
    def __init__(
        self, 
        agent_id: str, 
        config: Dict[str, Any], 
        event_bus: EventBus, 
        logger: logging.Logger,
        agent_manifest: Optional[List[Dict[str, str]]] = None
    ):
        """
        Initialize a base agent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Configuration dictionary
            event_bus: Event bus for communication
            logger: Logger instance
            agent_manifest: List of all agents and their goals for collaboration
        """
        self.agent_id = agent_id
        self.config = config
        self.event_bus = event_bus
        self.logger = logger
        self.agent_manifest = agent_manifest
        self.run_id = config.get("run_id", "unknown")
        self.is_running = False
        self.task = None
        
        # Subscribe to direct messages addressed to this agent
        self.event_bus.subscribe(EventType.AGENT_MESSAGE, self._handle_message)
        
    async def _handle_message(self, event: Event):
        """Handle direct messages from other agents."""
        # Check if this message is addressed to this agent
        if event.payload.get("to") != self.agent_id:
            return
            
        self.logger.info(
            f"Agent {self.agent_id} received message",
            extra={"from": event.agent_id, "payload": event.payload}
        )
        
        # Process the message (to be implemented by subclasses)
        await self._process_message(event)
        
    async def _process_message(self, event: Event):
        """Process a message from another agent (to be implemented by subclasses)."""
        # Default implementation just logs the message
        self.logger.debug(
            f"Message processing not implemented for {self.__class__.__name__}",
            extra={"event": event.dict()}
        )
        
    async def send_message(self, to_agent: str, payload: Dict[str, Any]):
        """Send a message to another agent."""
        full_payload = {**payload, "from": self.agent_id}
        self.logger.info(
            f"Agent {self.agent_id} sending message to {to_agent}",
            extra={"to": to_agent, "payload": full_payload}
        )
        await self.event_bus.send_message(to_agent, self.run_id, full_payload)
        
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        
        This method constructs the base system prompt that defines the agent's
        role and capabilities. Subclasses should extend this method to add
        specific instructions for their agent type.
        """
        prompt = f"""You are an AI assistant that is part of a team of specialized agents working together to achieve a common goal. Your specific role is defined by your agent ID: {self.agent_id}.

Your primary responsibility is to help accomplish the overarching team goal while focusing on your specific individual goal.

"""
        
        # Add team collaboration information if manifest is available
        if self.agent_manifest:
            prompt += """## Team Collaboration
You are part of a collaborative team of agents. You can communicate with other agents to coordinate efforts, request information, or delegate tasks.

To communicate with another agent, use the `send_message(to_agent: str, payload: dict)` function, where:
- `to_agent` is the agent_id of the recipient
- `payload` is a dictionary containing your message

Other agents can also send messages to you, and you will receive them automatically.

### Team Members
The following agents are working with you on this project:

"""
            # Format the agent manifest into a readable list
            for agent in self.agent_manifest:
                prompt += f"- **{agent['agent_id']}** ({agent['type']}): {agent['goal']}\n"
            
            prompt += "\nYou should coordinate with these agents to achieve the overall project goal efficiently.\n"
        
        return prompt
    
    @abstractmethod
    async def _run(self):
        """
        Main execution loop for the agent.
        
        This method should be implemented by subclasses to define the
        agent-specific behavior.
        """
        pass
        
    async def start(self):
        """Start the agent's execution."""
        if self.is_running:
            self.logger.warning(f"Agent {self.agent_id} is already running")
            return
            
        self.logger.info(f"Starting agent {self.agent_id}")
        self.is_running = True
        self.task = asyncio.create_task(self._run())
        
        try:
            await self.task
        except asyncio.CancelledError:
            self.logger.info(f"Agent {self.agent_id} was cancelled")
        except Exception as e:
            self.logger.error(f"Agent {self.agent_id} encountered an error: {e}")
            raise
        finally:
            self.is_running = False
            
    async def stop(self):
        """Stop the agent's execution."""
        if not self.is_running or not self.task:
            self.logger.warning(f"Agent {self.agent_id} is not running")
            return
            
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        finally:
            self.is_running = False
