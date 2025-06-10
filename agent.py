#!/usr/bin/env python3
"""
Agent - Core Agent Module

This module defines the Agent class that handles the core functionality
for understanding user requests, creating development plans, and executing them.
"""

import os
import logging
from typing import List, Dict, Optional, Any
import datetime
import time

from llm_interface import LLMInterface
from project_executor import ProjectExecutor


class Agent:
    """
    Agent class for automated coding project development.
    
    This class handles the core functionality of understanding user requests,
    creating development plans, and executing them step by step.
    """
    
    def __init__(self, project_dir: str, plan_file: str = "development_plan.md", model_name: Optional[str] = None):
        """
        Initialize the Agent.
        
        Args:
            project_dir: Directory where the project will be developed
            plan_file: Filename for the development plan
            model_name: Name of the language model to use (defaults to environment variable)
        """
        self.logger = logging.getLogger(__name__)
        self.project_dir = project_dir
        self.plan_file = plan_file
        self.current_step = 0
        self.plan_steps = []
        
        # Initialize LLM interface and project executor
        self.llm = LLMInterface(model_name=model_name)
        self.executor = ProjectExecutor(project_dir)
        
        self.logger.info(f"Agent initialized with project directory: {project_dir}")
    
    def understand_request(self, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze and understand the user's request.
        
        Args:
            user_prompt: The user's description of what they want to build
            
        Returns:
            A dictionary containing the parsed understanding of the request
        """
        self.logger.info("Understanding user request")
        
        # Use the LLM interface to understand the request
        understanding = self.llm.understand_user_request(user_prompt)
        
        self.logger.debug(f"Request understanding: {understanding}")
        return understanding
    
    def create_plan(self, understanding: Dict[str, Any]) -> List[str]:
        """
        Create a development plan based on the understood request.
        
        Args:
            understanding: The parsed understanding of the user's request
            
        Returns:
            A list of steps in the development plan
        """
        self.logger.info("Creating development plan")
        
        # Use the LLM interface to create a development plan
        steps = self.llm.create_development_plan(understanding)
        
        # Limit to max 10 steps
        if len(steps) > 10:
            self.logger.warning(f"Plan had {len(steps)} steps, truncating to 10")
            steps = steps[:10]
        
        # Save the plan to a file
        self._save_plan_to_file(steps)
        
        self.plan_steps = steps
        return steps
    
    def execute_step(self, step_index: int) -> bool:
        """
        Execute a specific step in the development plan.
        
        Args:
            step_index: The index of the step to execute
            
        Returns:
            True if the step was executed successfully, False otherwise
        """
        if step_index >= len(self.plan_steps):
            self.logger.error(f"Step index {step_index} out of range")
            return False
        
        step = self.plan_steps[step_index]
        self.logger.info(f"Executing step {step_index + 1}: {step}")
        
        # Get the current state of the project
        project_files = self.executor.list_files()
        
        # Plan the implementation of this step using the LLM
        implementation_plan = self.llm.plan_implementation_step(
            step_description=step,
            project_files=project_files,
            current_step_index=step_index,
            total_steps=len(self.plan_steps)
        )
        
        # Execute the implementation plan
        success = self._execute_implementation_plan(implementation_plan)
        
        if success:
            self.logger.info(f"Step {step_index + 1} completed successfully")
        else:
            self.logger.error(f"Failed to execute step {step_index + 1}")
        
        return success
    
    def _execute_implementation_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Execute an implementation plan.
        
        Args:
            plan: The implementation plan from the LLM
            
        Returns:
            True if the plan was executed successfully, False otherwise
        """
        # Create new files
        for file_path in plan.get('files_to_create', []):
            content = self.llm.generate_code(
                file_path=file_path,
                implementation_details=plan.get('implementation_details', '')
            )
            if not self.executor.create_file(file_path, content):
                return False
        
        # Modify existing files
        for file_path in plan.get('files_to_modify', []):
            existing_content = self.executor.read_file(file_path)
            if existing_content is None:
                self.logger.error(f"Cannot modify non-existent file: {file_path}")
                return False
            
            new_content = self.llm.generate_code(
                file_path=file_path,
                implementation_details=plan.get('implementation_details', ''),
                existing_content=existing_content
            )
            if not self.executor.modify_file(file_path, new_content):
                return False
        
        # Run any specified commands
        for command in plan.get('commands_to_run', []):
            return_code, stdout, stderr = self.executor.run_command(command)
            if return_code != 0:
                self.logger.error(f"Command failed: {command}\nError: {stderr}")
                return False
        
        return True
    
    def update_plan(self, step_index: int, status: str = "DONE") -> bool:
        """
        Update the status of a step in the development plan.
        
        Args:
            step_index: The index of the step to update
            status: The new status of the step (default: "DONE")
            
        Returns:
            True if the plan was updated successfully, False otherwise
        """
        if step_index >= len(self.plan_steps):
            self.logger.error(f"Step index {step_index} out of range")
            return False
        
        # Update the step in memory
        original_step = self.plan_steps[step_index]
        if not original_step.startswith("["):
            self.plan_steps[step_index] = f"[{status}] {original_step}"
        else:
            # If the step already has a status, replace it
            self.plan_steps[step_index] = f"[{status}]{original_step[original_step.find(']') + 1:]}"
        
        # Update the plan file
        self._save_plan_to_file(self.plan_steps)
        
        self.logger.info(f"Updated step {step_index + 1} status to {status}")
        return True
    
    def run(self, user_prompt: str) -> bool:
        """
        Run the full agent workflow from understanding to completion.
        
        Args:
            user_prompt: The user's description of what they want to build
            
        Returns:
            True if the project was completed successfully, False otherwise
        """
        self.logger.info("Starting agent workflow")
        
        # Step 1: Understand the request
        understanding = self.understand_request(user_prompt)
        
        # Step 2: Create a development plan
        self.create_plan(understanding)
        
        # Step 3: Execute each step in the plan
        for i in range(len(self.plan_steps)):
            print(f"\nExecuting step {i+1}/{len(self.plan_steps)}: {self.plan_steps[i]}")
            
            # Execute the step
            success = self.execute_step(i)
            if not success:
                self.logger.error(f"Failed to execute step {i + 1}")
                return False
            
            # Update the plan to mark the step as done
            self.update_plan(i)
            
            # Small delay between steps for readability
            time.sleep(1)
        
        self.logger.info("Project development completed successfully")
        return True
    
    def _save_plan_to_file(self, steps: List[str]) -> None:
        """Save the development plan to a file."""
        self.logger.info(f"Saving development plan to {self.plan_file}")
        
        plan_content = "# Development Plan\n\n"
        plan_content += f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for i, step in enumerate(steps):
            plan_content += f"{i+1}. {step}\n"
        
        plan_content += "\n## Progress\n"
        plan_content += "- [x] Plan created\n"
        
        # Update progress markers based on completed steps
        done_steps = sum(1 for step in steps if step.startswith("[DONE]"))
        if done_steps > 0:
            plan_content += "- [x] Implementation started\n"
        else:
            plan_content += "- [ ] Implementation started\n"
        
        if done_steps == len(steps):
            plan_content += "- [x] Implementation completed\n"
            plan_content += "- [ ] Testing requested\n"
        else:
            plan_content += "- [ ] Implementation completed\n"
            plan_content += "- [ ] Testing requested\n"
        
        # Use the project executor to write the file
        self.executor.create_file(self.plan_file, plan_content)
