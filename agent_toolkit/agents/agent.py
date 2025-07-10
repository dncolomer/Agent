#!/usr/bin/env python3
"""
Unified Agent Implementation for Agent Toolkit

This module provides a single, unified Agent class that can be used for
all agent types (builder, operator). The behavior of the agent is determined
by its goal and type, not by its class implementation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from agent_toolkit.events import Event


class Agent(BaseAgent):
    """
    Unified Agent implementation for all agent types.
    
    This class provides a generic implementation that works for all agent types
    (builder, operator). The specific behavior is determined by the agent's
    goal and type, which are specified in the configuration.
    """
    
    async def _run(self):
        """
        Main execution loop for the agent.
        
        This method implements the abstract _run method from BaseAgent.
        It performs the agent's core functionality based on its goal.
        """
        self.logger.info(f"Agent {self.agent_id} is starting")
        
        # Determine the agent's type and goal from the configuration
        agent_type = self.agent_id.split('-')[0]  # Extract type from ID (builder-1, operator-2, etc.)
        
        # Find this agent's configuration entry
        agent_entry = next(
            (a for a in self.config.get("agents", []) 
             if a.get("type") == agent_type and self._matches_agent_entry(a)),
            {}
        )
        
        goal = agent_entry.get("goal", "No specific goal defined")
        
        self.logger.info(
            f"Agent {self.agent_id} initialized with type={agent_type}, goal={goal}",
            extra={"agent_type": agent_type, "goal": goal}
        )
        
        # Log the overarching team goal if available
        team_goal = self.config.get("overarching_team_goal")
        if team_goal:
            self.logger.info(
                f"Overarching team goal: {team_goal}",
                extra={"team_goal": team_goal}
            )
        
        # Announce presence to other agents
        await self._announce_presence(agent_type, goal)
        
        # Main agent loop
        try:
            while self.is_running:
                # In a real implementation, this would include:
                # 1. Analyzing the current state
                # 2. Planning next actions
                # 3. Executing actions
                # 4. Collaborating with other agents
                
                # For now, just sleep and wait for messages
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            self.logger.info(f"Agent {self.agent_id} was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Agent {self.agent_id} encountered an error: {e}")
            raise
            
        self.logger.info(f"Agent {self.agent_id} has completed its tasks")
    
    def _matches_agent_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Check if this agent matches a configuration entry.
        
        This is used to find the specific configuration for this agent
        when multiple agents of the same type are defined.
        """
        # For now, just a simple match on type
        # In a more sophisticated implementation, we could match on other attributes
        return entry.get("type") in self.agent_id
    
    async def _announce_presence(self, agent_type: str, goal: str):
        """
        Announce this agent's presence to all other agents.
        
        This helps establish the collaborative network at startup.
        """
        if not self.agent_manifest:
            self.logger.warning("No agent manifest available, skipping announcements")
            return
            
        for agent in self.agent_manifest:
            if agent["agent_id"] != self.agent_id:
                await self.send_message(
                    agent["agent_id"],
                    {
                        "message": f"Hello from {self.agent_id}. I am a {agent_type} agent with the goal: {goal}. I'm ready to collaborate.",
                        "action": "announce",
                        "agent_type": agent_type,
                        "goal": goal
                    }
                )
    
    async def _process_message(self, event: Event):
        """
        Process a message from another agent.
        
        This method handles incoming messages from other agents,
        allowing for coordination and collaboration.
        
        Args:
            event: The event containing the message
        """
        sender = event.agent_id or "unknown"
        message = event.payload.get("message", "No message content")
        action = event.payload.get("action", "message")
        
        self.logger.info(
            f"Agent {self.agent_id} received {action} from {sender}: {message}",
            extra={"message": message, "sender": sender, "action": action}
        )
        
        # In a real implementation, this would include:
        # 1. Parsing the message content
        # 2. Taking appropriate action based on the message
        # 3. Sending a response if necessary
        
        # For now, just acknowledge receipt for regular messages (not announcements)
        if sender != "unknown" and action != "announce":
            await self.send_message(
                sender,
                {
                    "message": f"Message received by {self.agent_id}. I'll consider this in my planning.",
                    "action": "acknowledge"
                }
            )
