#!/usr/bin/env python3
"""
BuilderAgent - Agent for Code Generation and Project Building

This module defines the BuilderAgent, a specialized agent responsible for
interpreting project goals, generating code, and creating/modifying files
within the project directory.
"""

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from agent_toolkit.agents.base_agent import BaseAgent
# Import EventType from the dedicated events module to avoid circular dependency
from agent_toolkit.events import EventType
from llm_interface import LLMInterface
from project_executor import ProjectExecutor


class BuilderAgent(BaseAgent):
    """
    BuilderAgent is responsible for generating code and building project components.
    It uses the LLMInterface to interact with language models and the ProjectExecutor
    to perform file system operations.
    """

    def __init__(self,
                 agent_id: str,
                 config: Dict[str, Any],
                 event_bus: Any,  # EventBus type hint
                 logger: logging.Logger):
        """
        Initializes the BuilderAgent.

        Args:
            agent_id: A unique identifier for the agent instance.
            config: The configuration dictionary for the agent.
            event_bus: An instance of the EventBus for inter-agent communication.
            logger: A logger instance for the agent.
        """
        super().__init__(agent_id, config, event_bus, logger)
        
        # Extract model name and temperature from agent_id
        # Format expected: builder-{model_index}-{agent_index}
        # Example: builder-1-2 (second agent using first model)
        parts = agent_id.split('-')
        if len(parts) >= 3:
            try:
                model_index = int(parts[1]) - 1  # Convert to 0-based index
                agent_index = int(parts[2]) - 1  # Convert to 0-based index
                
                # Get the models configuration
                build_config = self.config.get("build", {})
                models_config = build_config.get("agents", {}).get("models", [])
                
                if 0 <= model_index < len(models_config):
                    model_config = models_config[model_index]
                    model_name = model_config.get("name")
                    temperature = model_config.get("temperature", build_config.get("agents", {}).get("temperature", 0.7))
                    self.individual_agent_goal = model_config.get("individual_agent_goal", "")
                else:
                    # Fallback to default model settings
                    model_name = None  # Will use default from .env
                    temperature = 0.7
                    self.individual_agent_goal = ""
            except (ValueError, IndexError):
                # Fallback if agent_id format is unexpected
                model_name = None
                temperature = 0.7
                self.individual_agent_goal = ""
        else:
            # Fallback if agent_id format is unexpected
            model_name = None
            temperature = 0.7
            self.individual_agent_goal = ""
        
        # Initialize LLM interface with the appropriate model
        self.llm = LLMInterface(model_name=model_name, temperature=temperature)
        
        # Initialize project executor
        project_dir = self.config.get("build", {}).get("constraints", {}).get("target_directory", "./output")
        self.executor = ProjectExecutor(project_dir)
        
        # Extract builder-specific configuration
        self.overarching_team_goal = self.config.get("build", {}).get("overarching_team_goal", "")
        
        self.logger.info(f"BuilderAgent {self.agent_id} initialized with model: {self.llm.model_name}")
        self.logger.debug(f"Overarching goal: {self.overarching_team_goal}")
        self.logger.debug(f"Individual goal: {self.individual_agent_goal}")

        # ------------------------------------------------------------------ #
        # Debug / tracing helpers                                            #
        # ------------------------------------------------------------------ #
        # A per-agent session UUID to correlate log lines belonging together
        self.session_id: str = str(uuid.uuid4())[:8]

    # ---------------------------------------------------------------------- #
    # Internal helper to produce uniform debug lines                         #
    # ---------------------------------------------------------------------- #
    def _dbg(self, message: str, **extra):
        """
        Convenience wrapper for debug-level logging that always injects the
        current `session_id` so logs can be easily filtered.
        """
        self.logger.debug(
            f"[{self.agent_id}|{self.session_id}] {message}",
            extra=extra,
        )

    async def start(self):
        """
        Starts the BuilderAgent's execution.
        This method will drive the code generation and file creation process.
        """
        self.logger.info(f"BuilderAgent {self.agent_id} starting build process.")
        self._dbg(
            "Model parameters",
            model=self.llm.model_name,
            temperature=self.llm.temperature,
        )
        await self.publish_event(EventType.BUILD_START, {"agent_model": self.llm.model_name})

        try:
            phase_start = time.time()
            # Ensure the target directory exists
            target_directory = self.config.get("build", {}).get("constraints", {}).get("target_directory", "./output")
            os.makedirs(target_directory, exist_ok=True)

            # Determine what files to generate based on the goals
            file_specs = await self._plan_files_to_generate()
            self._dbg(f"Planning returned {len(file_specs)} file specs")
            
            # Generate and create each file
            # Use enumerate so we can reference the step index for logging/debugging
            for idx, file_spec in enumerate(file_specs, start=1):
                file_path = file_spec["file_path"]
                file_description = file_spec["description"]
                step_start = time.time()
                
                await self.publish_event(EventType.BUILD_STEP_START, {
                    "file": file_path,
                    "description": file_description
                })
                
                try:
                    # Generate code for this file
                    code = await self._generate_code_for_file(file_path, file_description)
                    
                    # Create the file
                    if code:
                        success = self.executor.create_file(file_path, code)
                        if success:
                            self.logger.info(f"Created file: {file_path}")
                            await self.publish_event(EventType.BUILD_STEP_COMPLETED, {
                                "file": file_path,
                                "status": "success"
                            })
                        else:
                            self.logger.error(f"Failed to create file: {file_path}")
                            await self.publish_event(EventType.BUILD_STEP_FAILED, {
                                "file": file_path,
                                "status": "failed",
                                "error": "File creation failed"
                            })
                    else:
                        self.logger.error(f"Failed to generate code for: {file_path}")
                        await self.publish_event(EventType.BUILD_STEP_FAILED, {
                            "file": file_path,
                            "status": "failed",
                            "error": "Code generation failed"
                        })
                except Exception as e:
                    self.logger.exception(f"Error processing file {file_path}: {str(e)}")
                    await self.publish_event(EventType.BUILD_STEP_FAILED, {
                        "file": file_path,
                        "status": "failed",
                        "error": str(e)
                    })
                finally:
                    self._dbg(
                        f"Step {idx}/{len(file_specs)} finished",
                        file=file_path,
                        elapsed=round(time.time() - step_start, 2),
                    )
            
            # Build phase completed
            await self.publish_event(EventType.BUILD_COMPLETED, {
                "files_created": len(file_specs),
                "model": self.llm.model_name
            })
            self._dbg(
                "Build phase complete",
                total_elapsed=round(time.time() - phase_start, 2),
            )
            
        except Exception as e:
            self.logger.exception(f"BuilderAgent {self.agent_id} encountered an error: {str(e)}")
            await self.publish_event(EventType.BUILD_FAILED, {"error": str(e)})
            raise

    async def stop(self):
        """
        Stops the BuilderAgent's execution.
        Performs any necessary cleanup.
        """
        self.logger.info(f"BuilderAgent {self.agent_id} stopping.")
        # No specific cleanup needed for now, but this method is required by the BaseAgent interface

    async def _plan_files_to_generate(self) -> List[Dict[str, str]]:
        """
        Plans what files to generate based on the agent's goals.
        
        Returns:
            A list of file specifications, each containing a file_path and description.
        """
        self.logger.info(f"Planning files to generate based on goals.")
        plan_start = time.time()
        
        # Create a prompt that combines the overarching and individual goals
        system_prompt = """
        You are an expert software architect. Your task is to plan the files needed
        to implement a software project based on the provided goals.
        
        Respond with a JSON array of file specifications, where each specification has:
        - file_path: Relative path to the file
        - description: Brief description of the file's purpose and contents
        
        Focus on creating a coherent set of files that work together to achieve the goals.
        """
        
        prompt = f"""
        I need to plan the files for a software project with the following goals:
        
        OVERARCHING TEAM GOAL: {self.overarching_team_goal}
        
        MY INDIVIDUAL GOAL: {self.individual_agent_goal}
        
        Based on these goals, determine the most important files I should create.
        Return a JSON array of file specifications, where each specification has:
        - file_path: Relative path to the file
        - description: Brief description of the file's purpose and contents
        
        Example response format:
        [
            {{
                "file_path": "src/main.py",
                "description": "Main entry point that initializes the application"
            }},
            {{
                "file_path": "src/utils/helpers.py",
                "description": "Utility functions for data processing"
            }}
        ]
        
        Return between 3-5 files that I should focus on creating.
        """
        
        # Use the LLM to generate the plan
        response = self.llm.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        # Log raw prompt size and a trimmed preview to avoid huge logs
        self._dbg(
            "LLM plan request",
            prompt_preview=prompt[:120].replace("\n", " "),
            response_len=len(response),
        )
        
        # Parse the response to extract the file specifications
        try:
            import json
            import re
            
            # Try to extract JSON from the response
            json_match = re.search(r'\[.*\]', response.replace('\n', ' '), re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                file_specs = json.loads(json_str)
                self.logger.info(f"Successfully planned {len(file_specs)} files to generate.")
                self._dbg(
                    "Plan parsed OK",
                    files=[fs["file_path"] for fs in file_specs],
                    elapsed=round(time.time() - plan_start, 2),
                )
                return file_specs
            else:
                self.logger.warning("Failed to extract JSON from LLM response. Using fallback plan.")
                # Fallback to a simple default plan
                return [
                    {
                        "file_path": "main.py",
                        "description": "Main entry point for the application"
                    },
                    {
                        "file_path": "utils.py",
                        "description": "Utility functions and helpers"
                    },
                    {
                        "file_path": "README.md",
                        "description": "Project documentation and usage instructions"
                    }
                ]
        except Exception as e:
            self.logger.exception(f"Error parsing file plan: {str(e)}")
            # Fallback to a simple default plan
            return [
                {
                    "file_path": "main.py",
                    "description": "Main entry point for the application"
                },
                {
                    "file_path": "utils.py",
                    "description": "Utility functions and helpers"
                },
                {
                    "file_path": "README.md",
                    "description": "Project documentation and usage instructions"
                }
            ]

    async def _generate_code_for_file(self, file_path: str, file_description: str) -> str:
        """
        Generates code for a specific file based on the agent's goals.
        
        Args:
            file_path: Path to the file to generate
            file_description: Description of the file's purpose
            
        Returns:
            The generated code as a string
        """
        self.logger.info(f"Generating code for {file_path}")
        gen_start = time.time()
        
        # Create a prompt that specifies what code to generate
        system_prompt = f"""
        You are an expert software developer tasked with implementing a file for a software project.
        Generate clean, well-documented, production-ready code for the specified file.
        
        The code should:
        1. Be complete and functional
        2. Include proper error handling
        3. Follow best practices for the language
        4. Have clear comments explaining complex logic
        5. Be optimized for readability and maintainability
        """
        
        prompt = f"""
        Create the file: {file_path}
        
        File description: {file_description}
        
        This file is part of a project with the following goals:
        
        OVERARCHING TEAM GOAL: {self.overarching_team_goal}
        
        MY INDIVIDUAL GOAL: {self.individual_agent_goal}
        
        Generate the complete code for this file. Ensure it's well-structured, properly documented,
        and implements the functionality described.
        """
        
        # Use the LLM to generate the code
        code = self.llm.generate_code(
            file_path=file_path,
            implementation_details=prompt,
            existing_content=None  # This is a new file
        )

        self._dbg(
            "LLM code generation completed",
            file=file_path,
            code_chars=len(code),
            elapsed=round(time.time() - gen_start, 2),
        )
        
        return code
