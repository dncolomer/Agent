#!/usr/bin/env python3
"""
LLM Interface - Language Model Integration Module

This module provides an interface for interacting with Language Models through OpenRouter.
It handles API calls, response parsing, and error handling.
"""

import logging
import json
import os
import time
import re
from typing import Dict, List, Optional, Union, Any

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LLMInterface:
    """
    Interface for interacting with Language Models through OpenRouter.
    
    This class provides methods for generating text using LLMs for various
    agent tasks such as understanding requests, creating plans, and executing
    development steps.
    """
    
    def __init__(self, model_name: str = None, temperature: float = 0.7):
        """
        Initialize the LLM interface.
        
        Args:
            model_name: Name of the language model to use (defaults to env var or gpt-4)
            temperature: Controls randomness in generation (0.0 = deterministic, 1.0 = creative)
        """
        self.logger = logging.getLogger(__name__)
        
        # Load API configuration from environment variables
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
        
        # Set model name (priority: parameter > env var > default)
        self.model_name = model_name or os.getenv("DEFAULT_MODEL", "openai/gpt-4-turbo-preview")
        self.temperature = temperature
        
        if not self.api_key:
            self.logger.warning("OpenRouter API key not found. Please set OPENROUTER_API_KEY environment variable.")
        
        self.logger.info(f"Initialized LLM interface with model: {self.model_name}")
    
    def generate_text(self, prompt: str, max_tokens: int = 500, system_prompt: str = None) -> str:
        """
        Generate text based on a prompt using OpenRouter API.
        
        Args:
            prompt: The input prompt for text generation
            max_tokens: Maximum number of tokens to generate
            system_prompt: Optional system instructions for the model
            
        Returns:
            Generated text as a string
            
        Raises:
            RuntimeError: If API call fails or response cannot be parsed
        """
        self.logger.debug(f"Generating text with prompt: {prompt[:50]}...")
        
        if not self.api_key:
            self.logger.error("Cannot generate text: OpenRouter API key not configured")
            return f"[Error: OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable.]"
        
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/dncolomer/Agent",  # Identify your application
            "X-Title": "Agent Prototype"  # Name of your application
        }
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare the request body
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens
        }
        
        # Make the API request with retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30  # 30 second timeout
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    self.logger.error(f"Unexpected API response format: {result}")
                    return "[Error: Unexpected API response format]"
                
            except requests.exceptions.HTTPError as e:
                self.logger.error(f"HTTP error: {e}")
                if response.status_code == 429:  # Rate limit error
                    retry_after = int(response.headers.get("Retry-After", retry_delay))
                    self.logger.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                elif 500 <= response.status_code < 600:  # Server errors
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Server error. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                return f"[Error: HTTP error {response.status_code}]"
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error: {e}")
                if attempt < max_retries - 1:
                    self.logger.warning(f"Request failed. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                return "[Error: Failed to connect to OpenRouter API]"
                
            except json.JSONDecodeError:
                self.logger.error("Failed to parse API response")
                return "[Error: Invalid response from OpenRouter API]"
                
            except Exception as e:
                self.logger.exception(f"Unexpected error: {e}")
                return f"[Error: {str(e)}]"
        
        return "[Error: Maximum retries exceeded]"
    
    def understand_user_request(self, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze and understand a user's project request.
        
        Args:
            user_prompt: The user's description of what they want to build
            
        Returns:
            A dictionary containing the parsed understanding of the request
        """
        self.logger.info("Understanding user request using LLM")
        
        # Create a specialized prompt for the LLM
        system_prompt = """
        You are an expert software developer assistant. Your task is to analyze a project request
        and extract key information about what needs to be built.
        
        Respond with a JSON object containing the following fields:
        - project_type: The type of project (web, api, cli, mobile, etc.)
        - features: List of main features requested
        - technologies: List of technologies mentioned or implied
        - complexity: Estimated complexity (simple, moderate, complex)
        """
        
        llm_prompt = f"""
        Analyze the following project request and extract key information:
        
        USER REQUEST: {user_prompt}
        
        Extract and return ONLY a valid JSON object with the following fields:
        - project_type: The type of project (web, api, cli, etc.)
        - features: List of main features requested
        - technologies: List of technologies mentioned or implied
        - complexity: Estimated complexity (simple, moderate, complex)
        
        Do not include any explanations or text outside the JSON object.
        """
        
        # Get response from LLM
        response = self.generate_text(
            prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=1000
        )
        
        # Extract JSON from response
        try:
            # Find JSON content (might be surrounded by markdown code blocks or other text)
            json_content = response
            
            # If response contains markdown code blocks, extract the JSON
            if "```json" in response:
                json_content = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_content = response.split("```")[1].split("```")[0].strip()
                
            # Parse the JSON
            understanding = json.loads(json_content)
            
            # Add the raw prompt to the understanding
            understanding["raw_prompt"] = user_prompt
            
            return understanding
            
        except (json.JSONDecodeError, IndexError) as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Raw response: {response}")
            
            # Fallback to basic understanding
            return {
                "project_type": "generic",
                "features": ["basic_functionality"],
                "technologies": ["python"],
                "complexity": "simple",
                "raw_prompt": user_prompt,
                "parse_error": str(e)
            }
    
    def create_development_plan(self, understanding: Dict[str, Any]) -> List[str]:
        """
        Create a development plan based on project understanding.
        
        Args:
            understanding: The parsed understanding of the user's request
            
        Returns:
            A list of development steps (max 10)
        """
        self.logger.info("Creating development plan using LLM")
        
        # Extract information from understanding
        project_type = understanding.get("project_type", "generic")
        features = understanding.get("features", [])
        technologies = understanding.get("technologies", [])
        raw_prompt = understanding.get("raw_prompt", "")
        
        # Create a specialized prompt for the LLM
        system_prompt = """
        You are an expert software architect and project planner. Your task is to create
        a clear, step-by-step development plan for a software project.
        
        The plan should:
        1. Have at most 10 steps
        2. Be specific and actionable
        3. Cover the entire development process
        4. Be ordered logically from setup to completion
        """
        
        llm_prompt = f"""
        Create a development plan (maximum 10 steps) for the following project:
        
        PROJECT TYPE: {project_type}
        FEATURES: {', '.join(features)}
        TECHNOLOGIES: {', '.join(technologies)}
        USER REQUEST: {raw_prompt}
        
        Return a numbered list of development steps. Each step should be clear, specific and actionable.
        The steps should cover the entire development process from initial setup to completion.
        
        Format your response as a simple numbered list:
        1. First step
        2. Second step
        etc.
        
        Do not include any explanations or text outside the numbered list.
        """
        
        # Get response from LLM
        response = self.generate_text(
            prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=1500
        )
        
        # Process the response to extract the steps
        try:
            # Split the response into lines
            lines = response.strip().split('\n')
            
            # Extract steps (lines that start with a number followed by a period)
            steps = []
            for line in lines:
                line = line.strip()
                # Match lines that start with a number (possibly multiple digits) followed by a period or parenthesis
                if line and (line[0].isdigit() or 
                            (len(line) > 1 and line[0].isdigit() and 
                             (line[1] == '.' or line[1] == ')' or 
                              (len(line) > 2 and line[0:2].isdigit() and (line[2] == '.' or line[2] == ')')) or
                              (len(line) > 3 and line[0:3].isdigit() and (line[3] == '.' or line[3] == ')'))
                             ))):
                    # Remove the number and any leading/trailing whitespace
                    step_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                    if step_text:
                        steps.append(step_text)
            
            # If we couldn't extract steps using the above method, try another approach
            if not steps:
                # Look for lines that might be steps (non-empty lines that aren't headings)
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('```'):
                        steps.append(line)
            
            return steps
            
        except Exception as e:
            self.logger.error(f"Failed to parse development plan: {e}")
            self.logger.debug(f"Raw response: {response}")
            
            # Fallback to a basic plan
            return [
                "Set up project structure",
                "Create basic functionality",
                "Add error handling",
                "Write documentation"
            ]
    
    def plan_implementation_step(self, 
                               step_description: str, 
                               project_files: List[str],
                               current_step_index: int,
                               total_steps: int) -> Dict[str, Any]:
        """
        Plan the implementation of a specific development step.
        
        Args:
            step_description: Description of the step to implement
            project_files: List of existing files in the project
            current_step_index: Index of the current step (0-based)
            total_steps: Total number of steps in the plan
            
        Returns:
            A dictionary containing the implementation plan details
        """
        self.logger.info(f"Planning implementation for step: {step_description}")
        
        # Create a specialized prompt for the LLM
        system_prompt = """
        You are an expert software developer. Your task is to plan the implementation
        of a specific development step in a software project.
        
        Respond with a JSON object containing the following fields:
        - files_to_create: List of new files to create
        - files_to_modify: List of existing files to modify
        - implementation_details: Detailed description of the changes to make
        - commands_to_run: (Optional) List of commands to run
        """
        
        # Using a raw string for the JSON template to avoid backslash issues
        json_template = r'''
        {
          "files_to_create": ["path/to/file1.py", "path/to/file2.py"],
          "files_to_modify": ["path/to/existing.py"],
          "implementation_details": "Detailed description of what to implement",
          "commands_to_run": ["pip install package", "pytest tests/"]
        }
        '''
        
        llm_prompt = f"""
        Plan the implementation for the following development step:
        
        STEP {current_step_index + 1}/{total_steps}: {step_description}
        
        EXISTING FILES: {', '.join(project_files) if project_files else 'None'}
        
        Analyze the current step and existing files, then provide a detailed implementation plan.
        Return ONLY a valid JSON object with the following structure:
        {json_template}
        
        The "commands_to_run" field is optional. Include it only if necessary.
        Do not include any explanations or text outside the JSON object.
        """
        
        # Get response from LLM
        response = self.generate_text(
            prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=1500
        )
        
        # Extract JSON from response
        try:
            # Find JSON content (might be surrounded by markdown code blocks or other text)
            json_content = response
            
            # If response contains markdown code blocks, extract the JSON
            if "```json" in response:
                json_content = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_content = response.split("```")[1].split("```")[0].strip()
                
            # Parse the JSON
            implementation_plan = json.loads(json_content)
            
            # Ensure required fields exist
            implementation_plan.setdefault("files_to_create", [])
            implementation_plan.setdefault("files_to_modify", [])
            implementation_plan.setdefault("implementation_details", f"Implement {step_description}")
            
            return implementation_plan
            
        except (json.JSONDecodeError, IndexError) as e:
            self.logger.error(f"Failed to parse implementation plan: {e}")
            self.logger.debug(f"Raw response: {response}")
            
            # Fallback to a basic implementation plan
            return {
                "files_to_create": [f"{step_description.lower().replace(' ', '_')}.py"],
                "files_to_modify": [],
                "implementation_details": f"Create a new file implementing {step_description}"
            }
    
    def generate_code(self, 
                     file_path: str, 
                     implementation_details: str, 
                     existing_content: Optional[str] = None) -> str:
        """
        Generate code for a specific file.
        
        Args:
            file_path: Path of the file to generate code for
            implementation_details: Details of what to implement
            existing_content: Existing content of the file (if any)
            
        Returns:
            Generated code as a string
        """
        self.logger.info(f"Generating code for: {file_path}")
        
        # Determine file type from extension
        file_extension = file_path.split('.')[-1] if '.' in file_path else ''
        
        # Create a specialized prompt for the LLM that explicitly requests pure code output
        system_prompt = f"""
        You are an expert software developer tasked with generating clean, production-ready code.
        
        IMPORTANT INSTRUCTIONS:
        1. Output ONLY the raw code without any markdown formatting, code blocks, or explanatory text
        2. Do not include any text like "```python", "```", or language identifiers
        3. Do not include any explanations, comments about the code, or notes outside the actual code
        4. Start your response with the actual code - no preamble or introduction
        5. The code should be complete, functional, and follow best practices for {file_extension} files
        6. Include appropriate comments and documentation within the code itself
        7. Implement the requested functionality exactly as described
        
        Your entire response will be directly saved to a file, so it must contain ONLY valid {file_extension} code.
        """
        
        # Fix the f-string backslash issue by using string concatenation
        existing_content_text = 'EXISTING CONTENT:\n' + existing_content if existing_content else 'This is a new file.'
        
        llm_prompt = f"""
        Generate code for the following file: {file_path}
        
        IMPLEMENTATION DETAILS: {implementation_details}
        
        {existing_content_text}
        
        IMPORTANT: Output ONLY the raw code without any markdown formatting or explanatory text.
        Do not include ```python or ``` markers. Your response will be directly saved as {file_path}.
        
        Include appropriate comments, error handling, and follow best practices for the file type.
        If modifying existing content, preserve the overall structure while making the necessary changes.
        """
        
        # Get response from LLM with increased token limit for code
        response = self.generate_text(
            prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=4000  # Larger token limit for code generation
        )
        
        # Clean up the response to extract pure code
        code = self._clean_code_response(response, file_extension)
        
        return code
    
    def _clean_code_response(self, response: str, file_extension: str) -> str:
        """
        Clean up the LLM response to extract pure code.
        
        Args:
            response: The raw response from the LLM
            file_extension: The file extension (e.g., 'py', 'js')
            
        Returns:
            Clean code as a string
        """
        # Remove any markdown code blocks
        code = response
        
        # If the response contains markdown code blocks, extract just the code
        if "```" in response:
            # Try to extract code from a code block with language specifier
            language_blocks = [f"```{file_extension}", "```python", "```javascript", "```html", "```css", "```java", "```c"]
            for lang_block in language_blocks:
                if lang_block.lower() in response.lower():
                    parts = response.lower().split(lang_block.lower(), 1)
                    if len(parts) > 1:
                        code = parts[1].split("```", 1)[0].strip()
                        break
            
            # If no language-specific block found, try generic code block
            if code == response and "```" in response:
                parts = response.split("```", 2)
                if len(parts) > 2:
                    code = parts[1].strip()
                    
                    # If the first line looks like a language specifier, remove it
                    lines = code.split("\n")
                    if len(lines) > 0 and lines[0].strip().lower() in ["python", "javascript", "html", "css", "java", "c", "json"]:
                        code = "\n".join(lines[1:])
        
        # Remove common artifacts at the beginning of the file
        artifacts = ["thon", "python", "js", "javascript", "html", "css", "java", "c", "json"]
        for artifact in artifacts:
            if code.lower().startswith(artifact):
                code = code[len(artifact):].lstrip()
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        # For Python files, ensure proper shebang if it's missing
        if file_extension == 'py' and not code.startswith("#!/") and not code.startswith("#!"):
            code = f"#!/usr/bin/env python3\n{code}"
        
        # For shell scripts, ensure proper shebang
        if file_extension == 'sh' and not code.startswith("#!/"):
            code = f"#!/bin/bash\n{code}"
        
        return code
