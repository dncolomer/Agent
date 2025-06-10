#!/usr/bin/env python3
"""
Agent - Core Agent Module

This module defines the Agent class that handles the core functionality
for understanding user requests, creating development plans, and executing them.
"""

import os
import logging
from typing import List, Dict, Optional, Any, Tuple
import datetime
import time
import re

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
        
        # Create project directory if it doesn't exist
        os.makedirs(project_dir, exist_ok=True)
        
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
        
        # Adapt steps to work with our project structure
        adapted_steps = [self._adapt_step(step) for step in steps]
        
        # Save the plan to a file
        self._save_plan_to_file(adapted_steps)
        
        self.plan_steps = adapted_steps
        return adapted_steps
    
    def _adapt_step(self, step: str) -> str:
        """
        Adapt a step to work with the provided project directory.
        
        This method analyzes steps that involve directory creation or navigation
        and modifies them to work with our project structure.
        
        Args:
            step: The original step description
            
        Returns:
            The adapted step description
        """
        # Skip adaptation for steps that are already marked as done
        if step.startswith("[DONE]"):
            return step
            
        # Replace generic directory creation with project-specific instructions
        dir_creation_patterns = [
            r"create (?:a )?(?:new )?directory",
            r"mkdir",
            r"make (?:a )?(?:new )?directory"
        ]
        
        for pattern in dir_creation_patterns:
            if re.search(pattern, step.lower()):
                # Extract the directory name if possible
                dir_match = re.search(r"(?:called|named) ['\"](.*?)['\"]", step)
                if dir_match:
                    dir_name = dir_match.group(1)
                    return f"Create directory '{dir_name}' in the project"
                else:
                    return f"Set up project structure in {os.path.basename(self.project_dir)}"
        
        # Adapt steps that involve navigating to directories
        nav_patterns = [
            r"navigate (?:in)?to",
            r"cd ",
            r"change directory"
        ]
        
        for pattern in nav_patterns:
            if re.search(pattern, step.lower()):
                return f"Work within the project directory {os.path.basename(self.project_dir)}"
        
        # Adapt environment setup steps
        if "virtual environment" in step.lower() or "venv" in step.lower():
            return "Set up development environment"
            
        return step
    
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
        Execute an implementation plan with improved error handling.
        
        Args:
            plan: The implementation plan from the LLM
            
        Returns:
            True if the plan was executed successfully, False otherwise
        """
        # Track success of operations
        all_operations_succeeded = True
        failed_operations = []
        
        # Create new files
        for file_path in plan.get('files_to_create', []):
            try:
                content = self.llm.generate_code(
                    file_path=file_path,
                    implementation_details=plan.get('implementation_details', '')
                )
                
                # Validate generated content
                if not content or len(content.strip()) < 10:
                    self.logger.warning(f"Generated content for {file_path} seems too short or empty")
                    # Try one more time with more specific instructions
                    content = self.llm.generate_code(
                        file_path=file_path,
                        implementation_details=f"Create a complete, working {file_path} file that implements: {plan.get('implementation_details', '')}"
                    )
                
                # Create the file
                if not self.executor.create_file(file_path, content):
                    self.logger.error(f"Failed to create file: {file_path}")
                    all_operations_succeeded = False
                    failed_operations.append(f"Create {file_path}")
            except Exception as e:
                self.logger.exception(f"Error creating file {file_path}: {e}")
                all_operations_succeeded = False
                failed_operations.append(f"Create {file_path}")
        
        # Modify existing files
        for file_path in plan.get('files_to_modify', []):
            try:
                existing_content = self.executor.read_file(file_path)
                if existing_content is None:
                    self.logger.error(f"Cannot modify non-existent file: {file_path}")
                    all_operations_succeeded = False
                    failed_operations.append(f"Modify {file_path}")
                    continue
                
                new_content = self.llm.generate_code(
                    file_path=file_path,
                    implementation_details=plan.get('implementation_details', ''),
                    existing_content=existing_content
                )
                
                # Validate the modified content
                if not new_content or len(new_content.strip()) < 10:
                    self.logger.warning(f"Modified content for {file_path} seems too short or empty")
                    # Keep the original content instead
                    self.logger.info(f"Keeping original content for {file_path}")
                    continue
                
                if not self.executor.modify_file(file_path, new_content):
                    self.logger.error(f"Failed to modify file: {file_path}")
                    all_operations_succeeded = False
                    failed_operations.append(f"Modify {file_path}")
            except Exception as e:
                self.logger.exception(f"Error modifying file {file_path}: {e}")
                all_operations_succeeded = False
                failed_operations.append(f"Modify {file_path}")
        
        # Run any specified commands
        for command in plan.get('commands_to_run', []):
            try:
                # Skip potentially problematic commands
                if "cd " in command or "mkdir" in command:
                    self.logger.warning(f"Skipping directory manipulation command: {command}")
                    continue
                    
                return_code, stdout, stderr = self.executor.run_command(command)
                if return_code != 0:
                    self.logger.error(f"Command failed: {command}\nError: {stderr}")
                    all_operations_succeeded = False
                    failed_operations.append(f"Run command: {command}")
            except Exception as e:
                self.logger.exception(f"Error running command {command}: {e}")
                all_operations_succeeded = False
                failed_operations.append(f"Run command: {command}")
        
        # Log failed operations
        if failed_operations:
            self.logger.warning(f"The following operations failed: {', '.join(failed_operations)}")
            
        return all_operations_succeeded
    
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
                # Try to continue with the next step instead of failing completely
                self.update_plan(i, "FAILED")
                continue
            
            # Update the plan to mark the step as done
            self.update_plan(i)
            
            # Small delay between steps for readability
            time.sleep(1)
        
        # Check if any steps failed
        failed_steps = sum(1 for step in self.plan_steps if "[FAILED]" in step)
        if failed_steps > 0:
            self.logger.warning(f"Project completed with {failed_steps} failed steps")
            print(f"\nProject completed with {failed_steps} failed steps. Please check the plan file.")
        else:
            self.logger.info("Project development completed successfully")
        
        return failed_steps == 0
    
    def simple_run(self, user_prompt: str, main_file: str) -> Tuple[bool, str]:
        """
        Run a simplified workflow for very basic projects.
        
        This method skips the multi-step planning process and directly generates
        the requested file based on the user prompt.
        
        Args:
            user_prompt: The user's description of what they want to build
            main_file: The main file to create (e.g., "hello.py")
            
        Returns:
            Tuple of (success, file_content)
        """
        self.logger.info(f"Starting simple workflow to create {main_file}")
        
        # Create a simple plan
        plan_content = f"# Simple Development Plan\n\n"
        plan_content += f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        plan_content += f"1. Create {main_file} file that implements the requested functionality\n"
        
        # Save the simple plan
        self.executor.create_file(self.plan_file, plan_content)
        
        # Generate the file content
        try:
            file_content = self.llm.generate_code(
                file_path=main_file,
                implementation_details=user_prompt
            )
            
            # Create the file
            if self.executor.create_file(main_file, file_content):
                self.logger.info(f"Successfully created {main_file}")
                
                # Update the plan to mark the step as done
                plan_content = plan_content.replace(f"1. Create {main_file}", f"1. [DONE] Create {main_file}")
                self.executor.modify_file(self.plan_file, plan_content)
                
                return True, file_content
            else:
                self.logger.error(f"Failed to create {main_file}")
                return False, ""
                
        except Exception as e:
            self.logger.exception(f"Error in simple_run: {e}")
            return False, ""
    
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
        done_steps = sum(1 for step in steps if "[DONE]" in step)
        failed_steps = sum(1 for step in steps if "[FAILED]" in step)
        
        if done_steps > 0 or failed_steps > 0:
            plan_content += "- [x] Implementation started\n"
        else:
            plan_content += "- [ ] Implementation started\n"
        
        if done_steps + failed_steps == len(steps):
            plan_content += "- [x] Implementation completed\n"
            plan_content += "- [ ] Testing requested\n"
        else:
            plan_content += "- [ ] Implementation completed\n"
            plan_content += "- [ ] Testing requested\n"
        
        # Use the project executor to write the file
        self.executor.create_file(self.plan_file, plan_content)
