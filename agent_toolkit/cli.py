#!/usr/bin/env python3
"""
Agent Toolkit CLI

This module provides a command-line interface for the Agent Toolkit,
allowing users to run, validate, and monitor agent operations through
a simple command-line tool.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union

import click
import yaml

# Import from the agent_toolkit package
from agent_toolkit.orchestrator import ConfigValidator, Orchestrator, run_orchestrator


# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent_toolkit.cli")


def setup_logging(verbose: bool, log_file: Optional[str] = None):
    """Configure logging based on CLI options."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Reset handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(os.path.abspath(log_file))
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    # Determine file format based on extension
    if path.suffix.lower() in [".yaml", ".yml"]:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    elif path.suffix.lower() == ".json":
        with open(path, "r") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {path.suffix}")


def validate_config(config_path: str, output_format: str = "text") -> bool:
    """Validate configuration file against schema."""
    try:
        config = load_config(config_path)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        return False
        
    validator = ConfigValidator()
    is_valid, errors = validator.validate(config)
    
    if output_format == "json":
        result = {
            "valid": is_valid,
            "errors": errors,
            "config_path": config_path
        }
        click.echo(json.dumps(result, indent=2))
    else:
        if is_valid:
            click.echo(f"✅ Configuration is valid: {config_path}")
        else:
            click.echo(f"❌ Configuration is invalid: {config_path}")
            for i, error in enumerate(errors, 1):
                click.echo(f"  {i}. {error}")
                
    return is_valid


def parse_log_file(log_file: str, output_format: str = "text", filter_str: Optional[str] = None) -> None:
    """Parse and display structured logs."""
    if not os.path.exists(log_file):
        click.echo(f"Log file not found: {log_file}", err=True)
        return
        
    try:
        entries = []
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    entry = json.loads(line)
                    
                    # Apply filter if specified
                    if filter_str and filter_str not in json.dumps(entry):
                        continue
                        
                    entries.append(entry)
                except json.JSONDecodeError:
                    # Handle non-JSON lines
                    if filter_str and filter_str not in line:
                        continue
                    entries.append({"raw": line})
                    
        if output_format == "json":
            click.echo(json.dumps(entries, indent=2))
        else:
            for entry in entries:
                if "ts" in entry and "lvl" in entry and "msg" in entry:
                    # Format structured log entry
                    level = entry["lvl"]
                    color = {
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red"
                    }.get(level, "white")
                    
                    click.echo(
                        f"{entry['ts']} "
                        f"[{click.style(level, fg=color)}] "
                        f"{entry.get('module', 'unknown')}: "
                        f"{entry['msg']}"
                    )
                    
                    # Show additional data if present
                    if "data" in entry and isinstance(entry["data"], dict):
                        for k, v in entry["data"].items():
                            click.echo(f"  {k}: {v}")
                else:
                    # Raw or non-standard entry
                    click.echo(entry.get("raw", json.dumps(entry)))
                    
    except Exception as e:
        click.echo(f"Error parsing log file: {e}", err=True)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Agent Toolkit - A configuration-driven multi-agent orchestration system.
    
    This CLI tool provides commands to run, validate, and monitor agent operations
    based on a configuration file.
    """
    pass


@cli.command("run")
@click.argument("config", type=click.Path(exists=True, dir_okay=False))
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", "-l", type=click.Path(), help="Log file path")
@click.option("--dry-run", is_flag=True, help="Validate configuration without running")
@click.option("--timeout", "-t", type=int, default=0, help="Timeout in seconds (0 for no timeout)")
def run_command(config: str, verbose: bool, log_file: Optional[str], dry_run: bool, timeout: int):
    """
    Run the agent toolkit with the specified configuration file.
    
    The configuration file can be in YAML or JSON format and must follow
    the Agent Toolkit schema.
    """
    # Set up logging
    setup_logging(verbose, log_file)
    
    # Validate configuration
    if not validate_config(config, output_format="text"):
        sys.exit(1)
        
    if dry_run:
        click.echo("Dry run completed. Configuration is valid.")
        sys.exit(0)
        
    # Run the orchestrator
    click.echo(f"Starting Agent Toolkit with configuration: {config}")
    
    try:
        if timeout > 0:
            # Run with timeout
            async def run_with_timeout():
                try:
                    return await asyncio.wait_for(run_orchestrator(config), timeout)
                except asyncio.TimeoutError:
                    logger.error(f"Operation timed out after {timeout} seconds")
                    return False
                    
            success = asyncio.run(run_with_timeout())
        else:
            # Run without timeout
            success = asyncio.run(run_orchestrator(config))
            
        if success:
            click.echo("✅ Agent Toolkit run completed successfully")
            sys.exit(0)
        else:
            click.echo("❌ Agent Toolkit run failed")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Error running Agent Toolkit: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command("validate")
@click.argument("config", type=click.Path(exists=True, dir_okay=False))
@click.option("--format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format")
def validate_command(config: str, format: str):
    """
    Validate a configuration file against the schema.
    
    This command checks if the configuration file is valid according to the
    Agent Toolkit schema without running the orchestrator.
    """
    is_valid = validate_config(config, output_format=format)
    sys.exit(0 if is_valid else 1)


@cli.command("logs")
@click.argument("log_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--filter", help="Filter log entries containing this string")
@click.option("--follow", "-F", is_flag=True, help="Follow log file (similar to tail -f)")
def logs_command(log_file: str, format: str, filter: Optional[str], follow: bool):
    """
    Parse and display structured logs from a log file.
    
    This command reads a log file produced by the Agent Toolkit and displays
    the entries in a human-readable format or as JSON.
    """
    if follow:
        # Follow mode (similar to tail -f)
        click.echo(f"Following log file: {log_file} (Press Ctrl+C to stop)")
        
        # Get current file size
        file_size = os.path.getsize(log_file)
        
        try:
            while True:
                # Check if file size has changed
                current_size = os.path.getsize(log_file)
                
                if current_size > file_size:
                    # Read new content
                    with open(log_file, "r") as f:
                        f.seek(file_size)
                        new_content = f.read()
                        
                    # Process new lines
                    for line in new_content.splitlines():
                        if not line.strip():
                            continue
                            
                        try:
                            entry = json.loads(line)
                            
                            # Apply filter if specified
                            if filter and filter not in json.dumps(entry):
                                continue
                                
                            if format == "json":
                                click.echo(json.dumps(entry))
                            else:
                                if "ts" in entry and "lvl" in entry and "msg" in entry:
                                    level = entry["lvl"]
                                    color = {
                                        "DEBUG": "cyan",
                                        "INFO": "green",
                                        "WARNING": "yellow",
                                        "ERROR": "red",
                                        "CRITICAL": "red"
                                    }.get(level, "white")
                                    
                                    click.echo(
                                        f"{entry['ts']} "
                                        f"[{click.style(level, fg=color)}] "
                                        f"{entry.get('module', 'unknown')}: "
                                        f"{entry['msg']}"
                                    )
                        except json.JSONDecodeError:
                            # Handle non-JSON lines
                            if filter and filter not in line:
                                continue
                            click.echo(line)
                            
                    # Update file size
                    file_size = current_size
                    
                # Sleep briefly to avoid high CPU usage
                time.sleep(0.1)
        except KeyboardInterrupt:
            click.echo("\nStopped following log file")
    else:
        # Normal mode (read once)
        parse_log_file(log_file, output_format=format, filter_str=filter)


@cli.command("init")
@click.argument("output", type=click.Path(file_okay=True, dir_okay=False))
@click.option("--template", "-t", type=click.Choice(["minimal", "complete"]), default="minimal", help="Template type")
def init_command(output: str, template: str):
    """
    Initialize a new configuration file with a template.
    
    This command creates a new configuration file with a predefined template
    to help you get started with the Agent Toolkit.
    """
    # Check if file already exists
    if os.path.exists(output):
        if not click.confirm(f"File {output} already exists. Overwrite?"):
            click.echo("Aborted.")
            return
            
    # Determine file format based on extension
    path = Path(output)
    if path.suffix.lower() not in [".yaml", ".yml", ".json"]:
        click.echo(f"Unsupported file format: {path.suffix}. Please use .yaml, .yml, or .json", err=True)
        sys.exit(1)
        
    # Create template
    if template == "minimal":
        config = {
            "project": {
                "name": "my-project",
                "description": "A simple project created with Agent Toolkit"
            },
            "build": {
                "agents": {
                    "count": 1,
                    "model": "openai/gpt-4-turbo-preview",
                    "max_cost_usd": 5.0
                }
            },
            "logging": {
                "level": "info",
                "format": "json",
                "sink": {
                    "type": "stdout"
                }
            }
        }
    else:  # complete
        config = {
            "project": {
                "name": "my-project",
                "description": "A comprehensive project created with Agent Toolkit",
                "version": "0.1.0",
                "tags": ["example", "agent-toolkit"]
            },
            "build": {
                "agents": {
                    "count": 2,
                    "model": "openai/gpt-4-turbo-preview",
                    "max_cost_usd": 10.0,
                    "max_runtime_min": 30,
                    "temperature": 0.7
                },
                "constraints": {
                    "max_files": 20,
                    "allowed_languages": ["python", "javascript"],
                    "target_directory": "./output"
                }
            },
            "verify": {
                "strategy": "sequential",
                "agents": {
                    "count": 1,
                    "model": "anthropic/claude-3-sonnet"
                },
                "tests": [
                    {
                        "type": "unit",
                        "path": "tests/unit/"
                    },
                    {
                        "type": "integration",
                        "path": "tests/integration/"
                    }
                ],
                "thresholds": {
                    "min_test_coverage": 80.0,
                    "max_critical_issues": 0
                }
            },
            "operate": {
                "runtime": "local",
                "operator_agents": {
                    "count": 1,
                    "model": "openai/gpt-4-turbo-preview"
                },
                "monitoring": {
                    "interval_sec": 60,
                    "metrics": ["cpu_usage", "memory_usage"]
                }
            },
            "logging": {
                "level": "info",
                "format": "json",
                "sink": {
                    "type": "file",
                    "path": "logs/agent-toolkit.ndjson"
                }
            }
        }
        
    # Write to file
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
        
        if path.suffix.lower() in [".yaml", ".yml"]:
            with open(output, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        else:  # .json
            with open(output, "w") as f:
                json.dump(config, f, indent=2)
                
        click.echo(f"✅ Created configuration file: {output}")
    except Exception as e:
        click.echo(f"❌ Error creating configuration file: {e}", err=True)
        sys.exit(1)


@cli.command("version")
def version_command():
    """Display version information."""
    click.echo("Agent Toolkit v0.1.0")
    click.echo("© 2025 Agent Toolkit - MIT License")


if __name__ == "__main__":
    cli()
