#!/usr/bin/env python3
"""
Config - Configuration Management Module

This module provides functionality for managing configuration settings
for the Agent. It includes default settings and the ability to load
custom settings from a configuration file.
"""

import os
import logging
import json
import configparser
from typing import Dict, Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field, validator


class LLMConfig(BaseModel):
    """Configuration settings for the Language Model interface."""
    model_name: str = Field(default="placeholder-model", 
                           description="Name of the language model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0,
                              description="Controls randomness in generation (0.0 = deterministic, 1.0 = creative)")
    max_tokens: int = Field(default=1000, ge=1,
                           description="Maximum number of tokens to generate")
    api_key_env_var: str = Field(default="LLM_API_KEY",
                                description="Environment variable name for the LLM API key")


class ExecutorConfig(BaseModel):
    """Configuration settings for the Project Executor."""
    command_timeout: int = Field(default=30, ge=1,
                                description="Maximum time (seconds) to wait for commands to complete")
    max_file_size: int = Field(default=1024 * 1024, ge=1,
                              description="Maximum file size in bytes for read/write operations")
    safe_mode: bool = Field(default=True,
                           description="When enabled, restricts potentially dangerous operations")
    backup_files: bool = Field(default=True,
                              description="Create backups before modifying files")


class AgentConfig(BaseModel):
    """Configuration settings for the Agent."""
    project_dir: str = Field(default="./project",
                            description="Directory where the project will be developed")
    plan_file: str = Field(default="development_plan.md",
                          description="Filename for the development plan")
    max_steps: int = Field(default=10, ge=1, le=20,
                          description="Maximum number of steps in the development plan")
    step_delay: float = Field(default=1.0, ge=0.0,
                             description="Delay between steps in seconds")


class Config(BaseModel):
    """Main configuration class for the Agent."""
    agent: AgentConfig = Field(default_factory=AgentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    
    @validator('agent')
    def validate_project_dir(cls, v):
        """Ensure project directory is an absolute path."""
        v.project_dir = os.path.abspath(v.project_dir)
        return v


class ConfigManager:
    """
    Manages configuration settings for the Agent.
    
    This class handles loading, saving, and accessing configuration settings
    from various sources (defaults, config files, environment variables).
    """
    
    DEFAULT_CONFIG_PATHS = [
        "./agent_config.json",
        "./agent_config.ini",
        "~/.agent_config.json",
        "~/.agent_config.ini",
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the ConfigManager.
        
        Args:
            config_path: Path to a configuration file (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        
        # Load configuration from file if provided
        if config_path:
            self.load_config(config_path)
        else:
            # Try to load from default locations
            for path in self.DEFAULT_CONFIG_PATHS:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    self.load_config(expanded_path)
                    break
    
    def load_config(self, config_path: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            True if the configuration was loaded successfully, False otherwise
        """
        try:
            path = Path(config_path)
            if not path.exists():
                self.logger.warning(f"Configuration file not found: {config_path}")
                return False
            
            # Handle different file formats
            if path.suffix.lower() == '.json':
                return self._load_json_config(path)
            elif path.suffix.lower() == '.ini':
                return self._load_ini_config(path)
            else:
                self.logger.warning(f"Unsupported configuration file format: {path.suffix}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return False
    
    def _load_json_config(self, path: Path) -> bool:
        """Load configuration from a JSON file."""
        try:
            with open(path, 'r') as f:
                config_data = json.load(f)
            
            # Update configuration with loaded data
            self._update_config(config_data)
            self.logger.info(f"Loaded configuration from {path}")
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            return False
    
    def _load_ini_config(self, path: Path) -> bool:
        """Load configuration from an INI file."""
        try:
            parser = configparser.ConfigParser()
            parser.read(path)
            
            config_data = {}
            for section in parser.sections():
                config_data[section] = {}
                for key, value in parser[section].items():
                    # Try to parse values as JSON for complex types
                    try:
                        config_data[section][key] = json.loads(value)
                    except json.JSONDecodeError:
                        # If not valid JSON, use the string value
                        config_data[section][key] = value
            
            # Update configuration with loaded data
            self._update_config(config_data)
            self.logger.info(f"Loaded configuration from {path}")
            return True
            
        except configparser.Error as e:
            self.logger.error(f"Error parsing INI configuration: {e}")
            return False
    
    def _update_config(self, config_data: Dict[str, Any]) -> None:
        """Update configuration with loaded data."""
        # Update agent config
        if 'agent' in config_data:
            for key, value in config_data['agent'].items():
                if hasattr(self.config.agent, key):
                    setattr(self.config.agent, key, value)
        
        # Update LLM config
        if 'llm' in config_data:
            for key, value in config_data['llm'].items():
                if hasattr(self.config.llm, key):
                    setattr(self.config.llm, key, value)
        
        # Update executor config
        if 'executor' in config_data:
            for key, value in config_data['executor'].items():
                if hasattr(self.config.executor, key):
                    setattr(self.config.executor, key, value)
    
    def save_config(self, config_path: str) -> bool:
        """
        Save current configuration to a file.
        
        Args:
            config_path: Path where to save the configuration
            
        Returns:
            True if the configuration was saved successfully, False otherwise
        """
        try:
            path = Path(config_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
            
            # Handle different file formats
            if path.suffix.lower() == '.json':
                with open(path, 'w') as f:
                    json.dump(self.config.dict(), f, indent=2)
            elif path.suffix.lower() == '.ini':
                parser = configparser.ConfigParser()
                
                # Convert config to INI format
                config_dict = self.config.dict()
                for section, values in config_dict.items():
                    parser[section] = {}
                    for key, value in values.items():
                        parser[section][key] = json.dumps(value)
                
                with open(path, 'w') as f:
                    parser.write(f)
            else:
                self.logger.warning(f"Unsupported configuration file format: {path.suffix}")
                return False
            
            self.logger.info(f"Saved configuration to {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_config(self) -> Config:
        """
        Get the current configuration.
        
        Returns:
            The current configuration object
        """
        return self.config
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            config_updates: Dictionary with configuration updates
        """
        self._update_config(config_updates)
        self.logger.debug("Configuration updated")


# Create a global instance for easy access
config_manager = ConfigManager()

def get_config() -> Config:
    """
    Get the current configuration.
    
    Returns:
        The current configuration object
    """
    return config_manager.get_config()

def load_config(config_path: str) -> bool:
    """
    Load configuration from a file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        True if the configuration was loaded successfully, False otherwise
    """
    return config_manager.load_config(config_path)
