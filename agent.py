#!/usr/bin/env python3
"""
Unified Agent Implementation

This module provides a single, unified Agent class that can be used for
all agent types (builder, operator). The behavior of the agent is determined
by its goal and type, not by its class implementation.
"""

import asyncio
import logging
import os
import json
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path
import requests
from dotenv import load_dotenv

from base_agent import BaseAgent
from events import Event, EventType

# Load environment variables
load_dotenv()

class TaskStatus(str, Enum):
    """Status of a task in the agent's workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"  # New status for skipped dependencies

class Task:
    """Represents a single task that an agent needs to perform."""
    
    def __init__(self, id: str, description: str, dependencies: List[str] = None):
        self.id = id
        self.description = description
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.dependency_wait_start = None  # Track when we started waiting for dependencies
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to a dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a task from a dictionary."""
        task = cls(data["id"], data["description"], data.get("dependencies", []))
        task.status = data.get("status", TaskStatus.PENDING)
        task.result = data.get("result")
        task.error = data.get("error")
        task.created_at = data.get("created_at", time.time())
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        return task


class Agent(BaseAgent):
    """
    Unified Agent implementation for all agent types.
    
    This class provides a generic implementation that works for all agent types
    (builder, operator). The specific behavior is determined by the agent's
    goal and type, which are specified in the configuration.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], event_bus: Any, 
                 logger: logging.Logger, agent_manifest: Optional[List[Dict[str, str]]] = None):
        """
        Initialize the agent with enhanced capabilities.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Configuration dictionary
            event_bus: Event bus for communication
            logger: Logger instance
            agent_manifest: List of all agents and their goals for collaboration
        """
        super().__init__(agent_id, config, event_bus, logger, agent_manifest)
        
        # Extract agent type and goal
        self.agent_type = agent_id.split('-')[0]  # builder or operator
        self.agent_entry = next(
            (a for a in config.get("agents", []) 
             if a.get("type") == self.agent_type and self._matches_agent_entry(a)),
            {}
        )
        self.goal = self.agent_entry.get("goal", "No specific goal defined")
        # Default to env DEFAULT_MODEL or OpenRouter's **auto** selector
        # Must be prefixed with ``openrouter/`` so the API recognises it.
        self.model = self.agent_entry.get("model") or os.getenv("DEFAULT_MODEL", "openrouter/auto")
        self.temperature = self.agent_entry.get("temperature", 0.7)
        
        # Task management
        self.tasks: List[Task] = []
        self.current_task_index = 0
        self.planning_complete = False
        
        # For builder agents
        self.target_directory = config.get("constraints", {}).get("target_directory", "./output")
        
        # For operator agents
        self.test_results = {}
        
        # Dependency resolution settings
        self.max_dependency_wait_time = 60  # Maximum time to wait for a dependency in seconds
        self.external_dependency_timeout = 30  # Time to wait for external dependencies before skipping
        
        # LLM interface
        self.llm = None
        
    async def _initialize_llm(self):
        """
        Initialise the OpenRouter LLM interface.

        This agent strictly depends on the presence of an ``OPENROUTER_API_KEY``.
        If the key is missing, a ``RuntimeError`` is raised to stop execution.
        """
        self.logger.info(f"Initialising OpenRouter LLM interface for {self.agent_id} with model {self.model}")

        api_key = os.getenv("OPENROUTER_API_KEY")
        api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")

        if not api_key:
            error_msg = (
                "OPENROUTER_API_KEY environment variable is required but not set. "
                "Aborting agent initialisation."
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Configure OpenRouter interface
        self.llm = {
            "generate": self._openrouter_generate,
            "model": self.model,
            "temperature": self.temperature,
            "api_key": api_key,
            "api_base": api_base.rstrip("/")
        }

        self.logger.info(f"OpenRouter interface initialised for {self.agent_id}")
    
    async def _openrouter_generate(self, prompt: str, system_prompt: str = None, response_format: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate text using the OpenRouter API.

        Args:
            prompt:      The user prompt.
            system_prompt: Optional system prompt providing context.
            response_format: Optional structured output format specification.

        Returns:
            The generated assistant text, or a descriptive error string.
        """
        self.logger.info(f"Generating with OpenRouter for {self.agent_id}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.llm['api_key']}",
            "HTTP-Referer": "https://github.com/dncolomer/Agent",  # Required by OpenRouter
            "X-Title": f"Agent Toolkit - {self.agent_id}"  # Required by OpenRouter
        }

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.llm["model"],
            "messages": messages,
            "temperature": self.llm["temperature"]
        }
        
        # Add response format if specified
        if response_format:
            data["response_format"] = response_format

        try:
            resp = requests.post(
                f"{self.llm['api_base']}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            # ------------------------------------------------------------------ #
            # Helpful handling for common API errors                             #
            # ------------------------------------------------------------------ #
            if resp.status_code == 401:
                # Give the user a direct, actionable message for auth errors
                helpful_msg = (
                    "OpenRouter API returned 401 Unauthorized. "
                    "Please verify that your OPENROUTER_API_KEY environment "
                    "variable is set correctly, has not expired, and has "
                    "sufficient quota."
                )
                # Log raw body for debugging
                self.logger.debug(
                    f"OpenRouter 401 response body: {resp.text}",
                    extra={"agent_id": self.agent_id},
                )
                self.logger.error(helpful_msg, extra={"agent_id": self.agent_id})
                # Raise an explicit error so the orchestrator halts early
                raise RuntimeError(helpful_msg)
            elif resp.status_code == 400:
                # Handle Bad Request errors with detailed information
                helpful_msg = (
                    "OpenRouter API returned 400 Bad Request. "
                    "This typically means there's an issue with the request format, "
                    "invalid model name, or missing required parameters."
                )
                # Log raw body for debugging
                self.logger.debug(
                    f"OpenRouter 400 response body: {resp.text}",
                    extra={
                        "agent_id": self.agent_id,
                        "model": self.llm["model"],
                        "request_data": data
                    },
                )
                self.logger.error(helpful_msg, extra={"agent_id": self.agent_id})
                # Raise an explicit error with the response body
                raise RuntimeError(f"{helpful_msg} Response: {resp.text}")

            resp.raise_for_status()
            payload = resp.json()
            return payload["choices"][0]["message"]["content"]
        except Exception as exc:
            self.logger.error(
                f"Error generating with OpenRouter: {exc}",
                extra={"agent_id": self.agent_id}
            )
            return f"Error: {str(exc)}"
    
    async def _plan_tasks(self) -> bool:
        """
        Plan the tasks needed to achieve the agent's goal.
        
        This method uses the LLM to break down the agent's goal into
        specific tasks that can be executed.
        
        Returns:
            True if planning was successful, False otherwise
        """
        self.logger.info(f"Planning tasks for {self.agent_id} to achieve goal: {self.goal}")
        
        # Create a prompt for the LLM with explicit instructions about dependencies
        system_prompt = f"""You are an AI assistant helping to plan tasks for a {self.agent_type} agent with ID '{self.agent_id}'.
The agent's goal is: {self.goal}
The overall team goal is: {self.config.get('overarching_team_goal', 'Not specified')}

IMPORTANT INSTRUCTIONS:
1. Break down the goal into specific, actionable tasks.
2. Each task must have a unique ID prefixed with "{self.agent_id}-" (e.g., "{self.agent_id}-task1").
3. Tasks should ONLY depend on other tasks from THIS SAME AGENT. DO NOT create dependencies on tasks from other agents.
4. For operator agents: DO NOT create dependencies on builder agents' tasks. Assume all necessary files already exist.
5. Create a self-contained plan that this agent can execute independently.

Each task should have:
1. A unique ID (prefixed with the agent's ID)
2. A clear description
3. Dependencies (IDs of THIS AGENT'S tasks that must be completed before this one)

Respond with a JSON object containing an array of tasks. Example format:
{{
  "tasks": [
    {{"id": "{self.agent_id}-task1", "description": "First task description", "dependencies": []}},
    {{"id": "{self.agent_id}-task2", "description": "Second task description", "dependencies": ["{self.agent_id}-task1"]}},
    ...
  ]
}}
"""
        
        prompt = f"""Please create a detailed plan for a {self.agent_type} agent (ID: {self.agent_id}) with the following goal:
{self.goal}

The plan should be comprehensive and include all steps needed to achieve this goal.

IMPORTANT: Create a self-contained plan with tasks that ONLY depend on other tasks from this same agent.
DO NOT create dependencies on tasks from other agents.
"""
        
        try:
            # Generate the plan using the LLM
            response = await self.llm["generate"](
                prompt, 
                system_prompt,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            # Extract JSON from the response (in case it's wrapped in markdown or explanatory text)
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            else:
                # Try to find JSON without markdown formatting
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)
            
            plan_data = json.loads(response)
            
            # Create Task objects from the plan
            for task_data in plan_data.get("tasks", []):
                task_id = task_data["id"]
                
                # Ensure task IDs are prefixed with agent ID
                if not task_id.startswith(f"{self.agent_id}-"):
                    task_id = f"{self.agent_id}-{task_id}"
                
                # Process dependencies to ensure they're properly prefixed
                dependencies = []
                for dep in task_data.get("dependencies", []):
                    if not dep.startswith(f"{self.agent_id}-"):
                        dependencies.append(f"{self.agent_id}-{dep}")
                    else:
                        dependencies.append(dep)
                
                task = Task(
                    id=task_id,
                    description=task_data["description"],
                    dependencies=dependencies
                )
                self.tasks.append(task)
            
            self.logger.info(f"Created plan with {len(self.tasks)} tasks for {self.agent_id}")
            self.planning_complete = True
            
            # Publish the plan to the event bus
            await self.event_bus.publish(Event(
                type=EventType.AGENT_TASK_START,
                run_id=self.run_id,
                agent_id=self.agent_id,
                payload={
                    "action": "plan_created",
                    "tasks": [task.to_dict() for task in self.tasks]
                }
            ))
            
            # Announce the plan to other agents
            await self._broadcast_plan()
            
            return True
        except Exception as e:
            self.logger.error(f"Error planning tasks: {e}")
            return False
    
    async def _broadcast_plan(self):
        """Broadcast the agent's plan to all other agents."""
        if not self.agent_manifest:
            return
            
        for agent in self.agent_manifest:
            if agent["agent_id"] != self.agent_id:
                await self.send_message(
                    agent["agent_id"],
                    {
                        "action": "plan_update",
                        "message": f"{self.agent_id} has created a plan with {len(self.tasks)} tasks.",
                        "plan": [task.to_dict() for task in self.tasks]
                    }
                )
    
    async def _get_next_executable_task(self) -> Optional[Task]:
        """
        Get the next task that can be executed.
        
        This method checks dependencies and returns the first task
        that is ready to be executed. It includes timeout handling for
        dependencies that might never be satisfied.
        
        Returns:
            The next executable task, or None if no tasks are ready
        """
        if not self.tasks:
            return None
            
        current_time = time.time()
        
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
                
            # Check if all dependencies are completed
            dependencies_met = True
            external_dependencies = []
            
            for dep_id in task.dependencies:
                # Check if this is an internal dependency (from this agent)
                if dep_id.startswith(f"{self.agent_id}-"):
                    dep_task = next((t for t in self.tasks if t.id == dep_id), None)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        dependencies_met = False
                        break
                else:
                    # This is an external dependency (from another agent)
                    external_dependencies.append(dep_id)
            
            # If all internal dependencies are met, check external ones
            if dependencies_met and external_dependencies:
                # Start tracking wait time if not already started
                if task.dependency_wait_start is None:
                    task.dependency_wait_start = current_time
                    self.logger.info(f"Task {task.id} is waiting for external dependencies: {external_dependencies}")
                
                # Check if we've waited long enough for external dependencies
                wait_time = current_time - task.dependency_wait_start
                if wait_time >= self.external_dependency_timeout:
                    self.logger.warning(
                        f"Timeout waiting for external dependencies for task {task.id}. "
                        f"Skipping dependencies: {external_dependencies}"
                    )
                    # Clear external dependencies and proceed with the task
                    task.dependencies = [d for d in task.dependencies if d.startswith(f"{self.agent_id}-")]
                    return task
                else:
                    # Still waiting for external dependencies
                    continue
            
            if dependencies_met:
                return task
                
        # No ready tasks found, check for deadlocks
        pending_tasks = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        if pending_tasks:
            # Check if any task has been waiting too long
            for task in pending_tasks:
                if task.dependency_wait_start is None:
                    task.dependency_wait_start = current_time
                elif current_time - task.dependency_wait_start >= self.max_dependency_wait_time:
                    self.logger.warning(
                        f"Dependency wait timeout for task {task.id}. "
                        f"Proceeding with task execution despite unmet dependencies."
                    )
                    # Clear all dependencies and return this task
                    task.dependencies = []
                    return task
                    
        return None
    
    async def _execute_task(self, task: Task) -> bool:
        """
        Execute a specific task.
        
        This method executes the task based on the agent's type.
        Builder agents create files and code, while operator agents
        test and validate.
        
        Args:
            task: The task to execute
            
        Returns:
            True if the task was executed successfully, False otherwise
        """
        self.logger.info(f"Executing task {task.id}: {task.description}")
        
        # Mark task as in progress
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = time.time()
        
        # Notify other agents
        await self._report_progress(task)
        
        try:
            # Execute based on agent type
            if self.agent_type == "builder":
                success = await self._execute_builder_task(task)
            else:  # operator
                success = await self._execute_operator_task(task)
                
            # Update task status
            if success:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                self.logger.info(f"Task {task.id} completed successfully")
            else:
                task.status = TaskStatus.FAILED
                self.logger.error(f"Task {task.id} failed")
                
            # Notify other agents
            await self._report_progress(task)
            
            return success
        except Exception as e:
            self.logger.error(f"Error executing task {task.id}: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await self._report_progress(task)
            return False
    
    async def _execute_builder_task(self, task: Task) -> bool:
        """
        Execute a task for a builder agent.
        
        This method handles file creation, code generation, and other
        builder-specific operations.
        
        Args:
            task: The task to execute
            
        Returns:
            True if the task was executed successfully, False otherwise
        """
        self.logger.info(f"Builder agent {self.agent_id} executing task: {task.description}")
        
        # Create system prompt for the LLM with EXPLICIT file format instructions
        system_prompt = f"""You are an AI assistant helping a builder agent implement the following task:
{task.description}

The agent's goal is: {self.goal}
The overall team goal is: {self.config.get('overarching_team_goal', 'Not specified')}

IMPORTANT: You must respond with a JSON object containing an array of files to create. Each file should have:
1. A valid file path (relative to the target directory: {self.target_directory})
2. The complete content for that file

DO NOT use descriptive labels like "File 1:" or "File:" as part of file paths.
File paths should be actual paths like "app.py", "src/index.js", or "config/settings.json".

Example response format:
{{
  "files": [
    {{
      "path": "app.py",
      "content": "import flask\\n\\napp = flask.Flask(__name__)\\n\\n@app.route('/')\\ndef index():\\n    return 'Hello, world!'\\n\\nif __name__ == '__main__':\\n    app.run(debug=True)"
    }},
    {{
      "path": "requirements.txt",
      "content": "flask==2.0.1\\nrequests==2.26.0"
    }}
  ]
}}

ALWAYS use this exact JSON format. Do not include any explanatory text outside the JSON structure.
"""
        
        # Create prompt based on task description
        prompt = f"""I need to implement the following task:
{task.description}

Please provide the necessary code files to complete this task.

Target directory: {self.target_directory}

IMPORTANT: Respond ONLY with a JSON object containing an array of files to create.
Each file must have a proper file path (like "app.py" or "src/components/TodoList.js") and complete content.
Do not use descriptive labels like "File 1:" or "File:" in your response.
"""
        
        try:
            # Generate implementation using LLM with structured output
            response = await self.llm["generate"](
                prompt, 
                system_prompt,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            try:
                # First try direct JSON parsing
                file_data = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from markdown
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    file_data = json.loads(json_match.group(1))
                else:
                    raise ValueError(f"Could not parse JSON from response: {response[:100]}...")
            
            # Process the file operations from the structured response
            file_operations = []
            for file_info in file_data.get("files", []):
                path = file_info.get("path", "")
                content = file_info.get("content", "")
                
                # Skip invalid paths
                if not path or not self._is_valid_path(path):
                    self.logger.warning(f"Skipping invalid file path: {path}")
                    continue
                
                # Make path relative to target directory
                if not path.startswith(self.target_directory):
                    path = os.path.join(self.target_directory, path)
                
                # Check if file exists
                if os.path.exists(path):
                    file_operations.append({
                        "type": "modify",
                        "path": path,
                        "content": content
                    })
                else:
                    file_operations.append({
                        "type": "create",
                        "path": path,
                        "content": content
                    })
            
            # Execute file operations
            success = True
            for op in file_operations:
                if op["type"] == "create":
                    op_success = await self._create_file(op["path"], op["content"])
                    if not op_success:
                        success = False
                elif op["type"] == "modify":
                    op_success = await self._modify_file(op["path"], op["content"])
                    if not op_success:
                        success = False
            
            # If no valid file operations were found, use fallback parsing
            if not file_operations:
                self.logger.warning(f"No valid file operations found in structured response, falling back to regex parsing")
                file_operations = self._parse_file_operations(response)
                
                # Execute fallback file operations
                for op in file_operations:
                    if op["type"] == "create":
                        op_success = await self._create_file(op["path"], op["content"])
                        if not op_success:
                            success = False
                    elif op["type"] == "modify":
                        op_success = await self._modify_file(op["path"], op["content"])
                        if not op_success:
                            success = False
            
            # Store the result
            task.result = {
                "file_operations": file_operations,
                "success": success
            }
            
            return success
        except Exception as e:
            self.logger.error(f"Error executing builder task: {e}")
            return False
    
    async def _execute_operator_task(self, task: Task) -> bool:
        """
        Execute a task for an operator agent.
        
        This method handles testing, validation, and other
        operator-specific operations.
        
        Args:
            task: The task to execute
            
        Returns:
            True if the task was executed successfully, False otherwise
        """
        self.logger.info(f"Operator agent {self.agent_id} executing task: {task.description}")
        
        # Create system prompt for the LLM
        system_prompt = f"""You are an AI assistant helping an operator agent implement the following task:
{task.description}

The agent's goal is: {self.goal}
The overall team goal is: {self.config.get('overarching_team_goal', 'Not specified')}

You should provide detailed test plans, validation steps, or verification procedures.
Be specific about what to check and how to interpret results.

IMPORTANT: Respond with a JSON object containing an array of test operations to perform. Each operation should have:
1. A type ("command" or "file_check")
2. For commands: the command to execute
3. For file checks: the file path to check

Example response format:
{{
  "tests": [
    {{
      "type": "command",
      "command": "python -m pytest tests/"
    }},
    {{
      "type": "file_check",
      "path": "app.py"
    }}
  ]
}}

ALWAYS use this exact JSON format. Do not include any explanatory text outside the JSON structure.
"""
        
        # Create prompt based on task description
        prompt = f"""I need to test or validate the following:
{task.description}

Please provide me with a detailed test plan.

Target directory: {self.target_directory}

IMPORTANT: Respond ONLY with a JSON object containing an array of test operations to perform.
"""
        
        try:
            # Generate test plan using LLM with structured output
            response = await self.llm["generate"](
                prompt, 
                system_prompt,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            try:
                # First try direct JSON parsing
                test_data = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from markdown
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    test_data = json.loads(json_match.group(1))
                else:
                    raise ValueError(f"Could not parse JSON from response: {response[:100]}...")
            
            # Process the test operations from the structured response
            test_operations = []
            for test_info in test_data.get("tests", []):
                test_type = test_info.get("type", "")
                
                if test_type == "command":
                    command = test_info.get("command", "")
                    if command:
                        test_operations.append({
                            "type": "command",
                            "command": command
                        })
                elif test_type == "file_check":
                    path = test_info.get("path", "")
                    if path:
                        # Make path relative to target directory if needed
                        if not path.startswith(self.target_directory):
                            path = os.path.join(self.target_directory, path)
                        
                        test_operations.append({
                            "type": "file_check",
                            "path": path,
                            "expected_content": test_info.get("expected_content")
                        })
            
            # If no valid test operations were found, use fallback parsing
            if not test_operations:
                self.logger.warning(f"No valid test operations found in structured response, falling back to regex parsing")
                test_operations = self._parse_test_operations(response)
            
            # Execute test operations
            success = True
            test_results = []
            
            for op in test_operations:
                if op["type"] == "command":
                    result, output = await self._run_command(op["command"])
                    test_results.append({
                        "type": "command",
                        "command": op["command"],
                        "success": result,
                        "output": output
                    })
                    if not result:
                        success = False
                elif op["type"] == "file_check":
                    result, output = await self._check_file(op["path"], op.get("expected_content"))
                    test_results.append({
                        "type": "file_check",
                        "path": op["path"],
                        "success": result,
                        "output": output
                    })
                    if not result:
                        success = False
            
            # Store the result
            task.result = {
                "test_operations": test_operations,
                "test_results": test_results,
                "success": success
            }
            
            # Update the agent's test results
            self.test_results[task.id] = test_results
            
            return success
        except Exception as e:
            self.logger.error(f"Error executing operator task: {e}")
            return False
    
    def _parse_file_operations(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse file operations from an LLM response.
        
        This method extracts file paths and content from the LLM's response.
        
        Args:
            response: The LLM's response containing file operations
            
        Returns:
            List of file operations (create or modify)
        """
        operations = []
        
        # Look for file paths and content in the response
        # This is a simple implementation and could be improved

        # -------------------------- #
        # 1. Markdown code blocks    #
        # -------------------------- #
        file_blocks = re.findall(
            r'```(?:[\w-]+)?\s*(?:file|path|filepath|file path):\s*([^\n]+)\s*\n(.*?)```',
            response,
            re.IGNORECASE | re.DOTALL,
        )
        for path, content in file_blocks:
            # Clean up path
            path = os.path.normpath(path.strip().strip("`").strip("\"").strip("'"))
            if not self._is_valid_path(path):
                continue
            # Make path relative to target directory
            if not path.startswith(self.target_directory):
                path = os.path.join(self.target_directory, path)
            
            # Check if file exists
            if os.path.exists(path):
                operations.append({
                    "type": "modify",
                    "path": path,
                    "content": content.strip()
                })
            else:
                operations.append({
                    "type": "create",
                    "path": path,
                    "content": content.strip()
                })
        
        # If no file blocks found, look for other patterns
        if not operations:
            # --------------------------- #
            # 2. Heading-style sections   #
            # --------------------------- #
            sections = re.split(r'\n#{1,3}\s+', response)
            for section in sections:
                path_match = re.search(r'^([^\n]+)\s*\n', section)
                if path_match:
                    path = path_match.group(1).strip()
                    # Check if it looks like a file path
                    if self._is_valid_path(path):
                        # Make path relative to target directory
                        if not path.startswith(self.target_directory):
                            path = os.path.join(self.target_directory, path)
                        
                        # Extract content (everything after the first line)
                        content = section[path_match.end():].strip()
                        
                        # Check if file exists
                        if os.path.exists(path):
                            operations.append({
                                "type": "modify",
                                "path": path,
                                "content": content
                            })
                        else:
                            operations.append({
                                "type": "create",
                                "path": path,
                                "content": content
                            })
        
        # If still no operations found, create a single file based on the task
        if not operations:
            # Create a generic file name based on the agent ID
            path = os.path.join(self.target_directory, f"{self.agent_id}_output.txt")
            operations.append({
                "type": "create",
                "path": path,
                "content": response.strip()
            })
            
        return operations

    # ------------------------------------------------------------------ #
    # Helper: path validation                                            #
    # ------------------------------------------------------------------ #
    def _is_valid_path(self, path: str) -> bool:
        """
        Heuristic check whether the extracted *path* looks like a real file
        path versus a descriptive label produced by the LLM (e.g. ``File 1:``
        or ``1. File Path``).  This prevents creating junk files such as
        ``"File: `" or ``"1. File:"`` seen in earlier runs.

        The rules are intentionally simple – they cover the common formats we
        expect from the model while filtering out obvious non-paths.
        """
        if not path:
            return False

        p = path.strip()

        # Reject purely numeric or bullet labels like "1." or "2"
        if re.fullmatch(r"\d+\.?", p):
            return False

        # Reject lines that start with common labels (case-insensitive)
        bad_prefixes = [
            "file", "file:", "file path", "file path:", "file to modify", "file to modify:",
            "summary", "special", "target", "optional", "activate"
        ]
        if any(p.lower().startswith(bp.lower()) for bp in bad_prefixes):
            return False

        # Must contain a path separator OR an extension
        has_sep = ("/" in p) or ("\\" in p)
        has_ext = os.path.splitext(p)[1] != ""
        if not (has_sep or has_ext):
            return False

        # Finally, exclude pathological names with whitespace only
        if p in [".", ".."]:
            return False

        return True
    
    def _parse_test_operations(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse test operations from an LLM response.
        
        This method extracts test commands and file checks from the LLM's response.
        
        Args:
            response: The LLM's response containing test operations
            
        Returns:
            List of test operations (commands or file checks)
        """
        operations = []
        
        # Look for commands to run
        command_blocks = re.findall(r'```(?:bash|sh|shell)?\s*(.*?)```', response, re.DOTALL)
        for command in command_blocks:
            operations.append({
                "type": "command",
                "command": command.strip()
            })
        
        # Look for file checks
        file_checks = re.findall(r'Check (?:file|path):\s*([^\n]+)', response, re.IGNORECASE)
        for path in file_checks:
            # Make path relative to target directory
            if not path.startswith(self.target_directory):
                path = os.path.join(self.target_directory, path.strip())
                
            operations.append({
                "type": "file_check",
                "path": path
            })
            
        # If no operations found, create a generic file check
        if not operations:
            operations.append({
                "type": "file_check",
                "path": self.target_directory
            })
            
        return operations
    
    async def _create_file(self, path: str, content: str) -> bool:
        """
        Create a file with the given content.
        
        Args:
            path: Path to the file
            content: Content to write to the file
            
        Returns:
            True if the file was created successfully, False otherwise
        """
        self.logger.info(f"Creating file: {path}")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Write content to file
            with open(path, 'w') as f:
                f.write(content)
                
            return True
        except Exception as e:
            self.logger.error(f"Error creating file {path}: {e}")
            return False
    
    async def _modify_file(self, path: str, content: str) -> bool:
        """
        Modify an existing file with the given content.
        
        Args:
            path: Path to the file
            content: New content for the file
            
        Returns:
            True if the file was modified successfully, False otherwise
        """
        self.logger.info(f"Modifying file: {path}")
        
        try:
            # Check if file exists
            if not os.path.exists(path):
                self.logger.warning(f"File {path} does not exist, creating instead")
                return await self._create_file(path, content)
                
            # Write content to file
            with open(path, 'w') as f:
                f.write(content)
                
            return True
        except Exception as e:
            self.logger.error(f"Error modifying file {path}: {e}")
            return False
    
    async def _check_file(self, path: str, expected_content: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if a file exists and optionally compare its content.
        
        Args:
            path: Path to the file
            expected_content: Expected content of the file (optional)
            
        Returns:
            Tuple of (success, output)
        """
        self.logger.info(f"Checking file: {path}")
        
        try:
            # Check if file exists
            if not os.path.exists(path):
                return False, f"File {path} does not exist"
                
            # If expected content is provided, compare
            if expected_content:
                with open(path, 'r') as f:
                    actual_content = f.read()
                    
                if actual_content.strip() == expected_content.strip():
                    return True, f"File {path} exists and content matches"
                else:
                    return False, f"File {path} exists but content does not match"
            else:
                return True, f"File {path} exists"
        except Exception as e:
            self.logger.error(f"Error checking file {path}: {e}")
            return False, str(e)
    
    async def _run_command(self, command: str) -> Tuple[bool, str]:
        """
        Run a shell command and return the result.
        
        Args:
            command: Command to run
            
        Returns:
            Tuple of (success, output)
        """
        self.logger.info(f"Running command: {command}")
        
        try:
            # Run the command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return True, stdout
            else:
                return False, stderr
        except Exception as e:
            self.logger.error(f"Error running command {command}: {e}")
            return False, str(e)
    
    async def _report_progress(self, task: Task):
        """
        Report progress on a task to other agents.
        
        This method sends a message to all other agents with the
        current status of the task.
        
        Args:
            task: The task to report progress on
        """
        if not self.agent_manifest:
            return
            
        # Publish progress to event bus
        await self.event_bus.publish(Event(
            type=EventType.AGENT_TASK_COMPLETED if task.status == TaskStatus.COMPLETED else EventType.AGENT_TASK_FAILED,
            run_id=self.run_id,
            agent_id=self.agent_id,
            payload={
                "task_id": task.id,
                "task_description": task.description,
                "status": task.status,
                "result": task.result
            }
        ))
        
        # Send message to other agents
        for agent in self.agent_manifest:
            if agent["agent_id"] != self.agent_id:
                await self.send_message(
                    agent["agent_id"],
                    {
                        "action": "task_update",
                        "message": f"{self.agent_id} has {task.status} task {task.id}: {task.description}",
                        "task": task.to_dict()
                    }
                )
    
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
        
        # Initialize LLM
        await self._initialize_llm()
        
        # Main agent loop
        try:
            # Step 1: Plan tasks
            if not await self._plan_tasks():
                self.logger.error(f"Failed to plan tasks for {self.agent_id}")
                return
                
            # Step 2: Execute tasks
            while self.is_running:
                # Get next executable task
                task = await self._get_next_executable_task()
                
                if task:
                    # Execute the task
                    await self._execute_task(task)
                elif all(task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED] for task in self.tasks):
                    # All tasks are completed, failed, or skipped
                    self.logger.info(f"All tasks completed for {self.agent_id}")
                    break
                else:
                    # Wait for dependencies to be completed
                    self.logger.info(f"Waiting for dependencies to be completed for {self.agent_id}")
                    await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            self.logger.info(f"Agent {self.agent_id} was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Agent {self.agent_id} encountered an error: {e}")
            raise
            
        self.logger.info(f"Agent {self.agent_id} has completed its tasks")
        
        # Publish completion event
        await self.event_bus.publish(Event(
            type=EventType.AGENT_COMPLETED,
            run_id=self.run_id,
            agent_id=self.agent_id,
            payload={
                "tasks_completed": sum(1 for task in self.tasks if task.status == TaskStatus.COMPLETED),
                "tasks_failed": sum(1 for task in self.tasks if task.status == TaskStatus.FAILED),
                "total_tasks": len(self.tasks)
            }
        ))
    
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
        
        # Process based on action type
        if action == "announce":
            # Just acknowledge
            await self.send_message(
                sender,
                {
                    "message": f"Hello {sender}, {self.agent_id} acknowledges your presence.",
                    "action": "acknowledge"
                }
            )
        elif action == "plan_update":
            # Another agent has shared their plan
            self.logger.info(f"Received plan update from {sender}")
            # In a more sophisticated implementation, we could adjust our own plan
            # based on the other agent's plan
            await self.send_message(
                sender,
                {
                    "message": f"{self.agent_id} acknowledges your plan.",
                    "action": "acknowledge"
                }
            )
        elif action == "task_update":
            # Another agent has updated a task
            task_data = event.payload.get("task", {})
            self.logger.info(f"Received task update from {sender}: {task_data.get('id')} - {task_data.get('status')}")
            
            # Check if this affects our own tasks
            if self.planning_complete:
                for task in self.tasks:
                    # If we have a task that depends on the updated task
                    if sender in task.dependencies and task_data.get("status") == TaskStatus.COMPLETED:
                        self.logger.info(f"Dependency {sender} completed, checking if task {task.id} can now be executed")
                        # No need to do anything here, the main loop will check dependencies
            
            await self.send_message(
                sender,
                {
                    "message": f"{self.agent_id} acknowledges your task update.",
                    "action": "acknowledge"
                }
            )
        elif action == "request_help":
            # Another agent is requesting help
            help_request = event.payload.get("request", "")
            self.logger.info(f"Received help request from {sender}: {help_request}")
            
            # Generate a response using the LLM
            system_prompt = f"""You are an AI assistant helping a {self.agent_type} agent respond to a help request.
The agent's goal is: {self.goal}
The overall team goal is: {self.config.get('overarching_team_goal', 'Not specified')}

Another agent has requested help with: {help_request}

Provide a helpful response based on your expertise and goal.
"""
            
            prompt = f"""Another agent ({sender}) has requested help with:
{help_request}

Please provide a helpful response based on my expertise and goal.
"""
            
            try:
                response = await self.llm["generate"](prompt, system_prompt)
                
                await self.send_message(
                    sender,
                    {
                        "message": response,
                        "action": "help_response",
                        "original_request": help_request
                    }
                )
            except Exception as e:
                self.logger.error(f"Error generating help response: {e}")
                await self.send_message(
                    sender,
                    {
                        "message": f"I'm sorry, but I encountered an error while trying to help: {e}",
                        "action": "help_response",
                        "original_request": help_request
                    }
                )
        else:
            # Default response for other message types
            await self.send_message(
                sender,
                {
                    "message": f"Message received by {self.agent_id}. I'll consider this in my planning.",
                    "action": "acknowledge"
                }
            )
