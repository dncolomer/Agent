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
        # Default to env DEFAULT_MODEL or OpenRouter's ``auto`` selector
        self.model = self.agent_entry.get("model") or os.getenv("DEFAULT_MODEL", "auto")
        self.temperature = self.agent_entry.get("temperature", 0.7)
        
        # Task management
        self.tasks: List[Task] = []
        self.current_task_index = 0
        self.planning_complete = False
        
        # For builder agents
        self.target_directory = config.get("constraints", {}).get("target_directory", "./output")
        
        # For operator agents
        self.test_results = {}
        
        # LLM interface
        self.llm = None
        
    async def _initialize_llm(self):
        """
        Initialise a single OpenRouter LLM interface (with mock fallback).
        """
        self.logger.info(f"Initialising OpenRouter LLM interface for {self.agent_id} with model {self.model}")

        api_key = os.getenv("OPENROUTER_API_KEY")
        api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")

        if not api_key:
            self.logger.warning("OPENROUTER_API_KEY not set – falling back to mock LLM.")
            self.llm = self._mock_llm_interface()
            return

        # Configure OpenRouter interface
        self.llm = {
            "generate": self._openrouter_generate,
            "model": self.model,
            "temperature": self.temperature,
            "api_key": api_key,
            "api_base": api_base.rstrip("/")
        }

        self.logger.info(f"OpenRouter interface initialised for {self.agent_id}")
    
    def _mock_llm_interface(self):
        """Create a mock LLM interface for testing."""
        return {
            "generate": self._mock_generate,
            "model": "mock-model",
            "temperature": self.temperature
        }
        
    async def _mock_generate(self, prompt: str, system_prompt: str = None) -> str:
        """Mock LLM generation for testing."""
        self.logger.info(f"Mock LLM generating response for {self.agent_id}")
        
        # Simple responses based on prompt content
        if "plan" in prompt.lower():
            if self.agent_type == "builder":
                return json.dumps({
                    "tasks": [
                        {"id": "task1", "description": "Analyze requirements", "dependencies": []},
                        {"id": "task2", "description": "Set up project structure", "dependencies": ["task1"]},
                        {"id": "task3", "description": "Implement core functionality", "dependencies": ["task2"]},
                        {"id": "task4", "description": "Add error handling", "dependencies": ["task3"]},
                        {"id": "task5", "description": "Write documentation", "dependencies": ["task4"]}
                    ]
                })
            else:  # operator
                return json.dumps({
                    "tasks": [
                        {"id": "task1", "description": "Verify project structure", "dependencies": []},
                        {"id": "task2", "description": "Test core functionality", "dependencies": ["task1"]},
                        {"id": "task3", "description": "Validate error handling", "dependencies": ["task2"]},
                        {"id": "task4", "description": "Check documentation", "dependencies": ["task3"]}
                    ]
                })
        elif "execute" in prompt.lower():
            return "Task execution simulated successfully."
        elif "file" in prompt.lower():
            return "print('Hello, world!')"
        else:
            return "I've processed your request and am ready to assist with the next steps."
    
    async def _openrouter_generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate text using the OpenRouter API.

        Args:
            prompt:      The user prompt.
            system_prompt: Optional system prompt providing context.

        Returns:
            The generated assistant text, or a descriptive error string.
        """
        self.logger.info(f"Generating with OpenRouter for {self.agent_id}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.llm['api_key']}"
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

        try:
            resp = requests.post(
                f"{self.llm['api_base']}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
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
        
        # Create a prompt for the LLM
        system_prompt = f"""You are an AI assistant helping to plan tasks for a {self.agent_type} agent.
The agent's goal is: {self.goal}
The overall team goal is: {self.config.get('overarching_team_goal', 'Not specified')}

Please break down this goal into specific, actionable tasks. Each task should have:
1. A unique ID
2. A clear description
3. Dependencies (IDs of tasks that must be completed before this one)

Respond with a JSON object containing an array of tasks. Example format:
{{
  "tasks": [
    {{"id": "task1", "description": "First task description", "dependencies": []}},
    {{"id": "task2", "description": "Second task description", "dependencies": ["task1"]}},
    ...
  ]
}}
"""
        
        prompt = f"""Please create a detailed plan for a {self.agent_type} agent with the following goal:
{self.goal}

The plan should be comprehensive and include all steps needed to achieve this goal.
"""
        
        try:
            # Generate the plan using the LLM
            response = await self.llm["generate"](prompt, system_prompt)
            
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
                task = Task(
                    id=task_data["id"],
                    description=task_data["description"],
                    dependencies=task_data.get("dependencies", [])
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
        that is ready to be executed.
        
        Returns:
            The next executable task, or None if no tasks are ready
        """
        if not self.tasks:
            return None
            
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
                
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in task.dependencies:
                dep_task = next((t for t in self.tasks if t.id == dep_id), None)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    dependencies_met = False
                    break
                    
            if dependencies_met:
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
        
        # Create system prompt for the LLM
        system_prompt = f"""You are an AI assistant helping a builder agent implement the following task:
{task.description}

The agent's goal is: {self.goal}
The overall team goal is: {self.config.get('overarching_team_goal', 'Not specified')}

You should provide detailed, implementable code or content that the agent can use to complete this task.
Be specific and provide complete implementations.
"""
        
        # Create prompt based on task description
        prompt = f"""I need to implement the following task:
{task.description}

Please provide me with the necessary code, file content, or instructions to complete this task.
Include file paths, code snippets, and any other details needed for implementation.

For each file that needs to be created or modified, provide:
1. The file path
2. The complete content of the file
3. Any special instructions for implementation

Target directory: {self.target_directory}
"""
        
        # Generate implementation using LLM
        response = await self.llm["generate"](prompt, system_prompt)
        
        # Parse the response to extract file operations
        file_operations = self._parse_file_operations(response)
        
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
                    
        # Store the result
        task.result = {
            "file_operations": file_operations,
            "success": success
        }
        
        return success
    
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
"""
        
        # Create prompt based on task description
        prompt = f"""I need to test or validate the following:
{task.description}

Please provide me with a detailed test plan, including:
1. What files or components to test
2. How to test them (commands, procedures, etc.)
3. What results to expect
4. How to interpret the results

Target directory: {self.target_directory}
"""
        
        # Generate test plan using LLM
        response = await self.llm["generate"](prompt, system_prompt)
        
        # Parse the response to extract test operations
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
        
        # Look for markdown code blocks with file paths
        file_blocks = re.findall(r'```(?:[\w-]+)?\s*(?:File|PATH|FILEPATH):\s*([^\n]+)\s*\n(.*?)```', response, re.DOTALL)
        for path, content in file_blocks:
            # Clean up path
            path = path.strip()
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
            # Look for sections with file paths and content
            sections = re.split(r'\n#{1,3}\s+', response)
            for section in sections:
                path_match = re.search(r'^([^\n]+)\s*\n', section)
                if path_match:
                    path = path_match.group(1).strip()
                    # Check if it looks like a file path
                    if '/' in path or '.' in path:
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
                elif all(task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] for task in self.tasks):
                    # All tasks are completed or failed
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
