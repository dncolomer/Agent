#!/usr/bin/env python3
"""
Orchestration Engine for Agent Toolkit

This module provides the core orchestration capabilities for the Agent Toolkit.
It handles configuration loading and validation, agent lifecycle management,
inter-agent communication, resource tracking, and structured logging.
"""

import asyncio
import datetime
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import jsonschema
import yaml
from pydantic import BaseModel, Field, ValidationError

# Import concrete agent implementations
from agent_toolkit.agents import BaseAgent, BuilderAgent, VerifierAgent
# from agent_toolkit.agents.operator import OperatorAgent

# Import event primitives from dedicated module
from agent_toolkit.events import EventType, Event, EventBus

# --------------------------------------------------------------------------- #
class OperatorAgent(BaseAgent):
    """Placeholder for the OperatorAgent class."""
    pass


class ResourceTracker:
    """
    Tracks and enforces resource constraints for agents.
    
    This class monitors token usage, cost, and runtime to ensure agents
    stay within the configured limits.
    """
    
    def __init__(self, config: Dict[str, Any], event_bus: EventBus, logger: logging.Logger):
        self.config = config
        self.event_bus = event_bus
        self.logger = logger
        self.start_time = time.time()
        
        # Extract limits from config
        # Limits are now defined under build.constraints (schema update)
        build_cfg = config.get("build", {})
        constraints_cfg = build_cfg.get("constraints", {})

        self.max_cost_usd = constraints_cfg.get("max_cost_usd", float("inf"))
        self.max_runtime_min = constraints_cfg.get("max_runtime_min", float("inf"))
        
        # Initialize counters
        self.current_cost_usd = 0.0
        self.token_usage = {"prompt": 0, "completion": 0, "total": 0}
        
        # Warning thresholds (80% of limit)
        self.cost_warning_threshold = self.max_cost_usd * 0.8
        self.time_warning_threshold = self.max_runtime_min * 60 * 0.8  # Convert to seconds
        
        # Track warnings already sent
        self.cost_warning_sent = False
        self.time_warning_sent = False
        
    def add_token_usage(self, prompt_tokens: int, completion_tokens: int, cost_usd: float, agent_id: str, run_id: str):
        """Add token usage and cost for an agent."""
        self.token_usage["prompt"] += prompt_tokens
        self.token_usage["completion"] += completion_tokens
        self.token_usage["total"] += prompt_tokens + completion_tokens
        self.current_cost_usd += cost_usd
        
        self.logger.info(
            f"Token usage updated: +{prompt_tokens + completion_tokens} tokens, +${cost_usd:.4f}",
            extra={
                "agent_id": agent_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
                "total_cost_usd": self.current_cost_usd,
                "total_tokens": self.token_usage["total"]
            }
        )
        
        # Check if we're approaching limits
        asyncio.create_task(self._check_limits(run_id))
        
    async def _check_limits(self, run_id: str):
        """Check if resource limits are being approached or exceeded."""
        # Check cost limits
        if self.current_cost_usd >= self.max_cost_usd:
            await self.event_bus.publish(Event(
                type=EventType.RESOURCE_LIMIT_EXCEEDED,
                run_id=run_id,
                payload={
                    "limit_type": "cost",
                    "current": self.current_cost_usd,
                    "limit": self.max_cost_usd,
                    "unit": "USD"
                }
            ))
        elif self.current_cost_usd >= self.cost_warning_threshold and not self.cost_warning_sent:
            self.cost_warning_sent = True
            await self.event_bus.publish(Event(
                type=EventType.RESOURCE_LIMIT_WARNING,
                run_id=run_id,
                payload={
                    "limit_type": "cost",
                    "current": self.current_cost_usd,
                    "limit": self.max_cost_usd,
                    "percentage": (self.current_cost_usd / self.max_cost_usd) * 100,
                    "unit": "USD"
                }
            ))
            
        # Check time limits
        elapsed_seconds = time.time() - self.start_time
        if elapsed_seconds >= self.max_runtime_min * 60:
            await self.event_bus.publish(Event(
                type=EventType.RESOURCE_LIMIT_EXCEEDED,
                run_id=run_id,
                payload={
                    "limit_type": "time",
                    "current": elapsed_seconds,
                    "limit": self.max_runtime_min * 60,
                    "unit": "seconds"
                }
            ))
        elif elapsed_seconds >= self.time_warning_threshold and not self.time_warning_sent:
            self.time_warning_sent = True
            await self.event_bus.publish(Event(
                type=EventType.RESOURCE_LIMIT_WARNING,
                run_id=run_id,
                payload={
                    "limit_type": "time",
                    "current": elapsed_seconds,
                    "limit": self.max_runtime_min * 60,
                    "percentage": (elapsed_seconds / (self.max_runtime_min * 60)) * 100,
                    "unit": "seconds"
                }
            ))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of resource usage."""
        elapsed_seconds = time.time() - self.start_time
        return {
            "elapsed_time": {
                "seconds": elapsed_seconds,
                "minutes": elapsed_seconds / 60,
                "percentage": (elapsed_seconds / (self.max_runtime_min * 60)) * 100 if self.max_runtime_min < float("inf") else 0
            },
            "cost": {
                "usd": self.current_cost_usd,
                "percentage": (self.current_cost_usd / self.max_cost_usd) * 100 if self.max_cost_usd < float("inf") else 0
            },
            "tokens": self.token_usage
        }


class StructuredLogger:
    """
    Provides structured logging capabilities for the Agent Toolkit.
    
    This class handles formatting log messages as JSON and routing them
    to the configured sinks (stdout, file, HTTP).
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("logging", {})
        self.level = getattr(logging, self.config.get("level", "info").upper())
        self.format = self.config.get("format", "json")
        
        # Configure the root logger
        self.logger = logging.getLogger("agent_toolkit")
        self.logger.setLevel(self.level)
        self.logger.handlers = []  # Remove any existing handlers
        
        # Add handlers based on configuration
        self._configure_handlers()
        
    def _configure_handlers(self):
        """Configure log handlers based on the configuration."""
        sink_config = self.config.get("sink", {"type": "stdout"})
        sink_type = sink_config.get("type", "stdout")
        
        if sink_type == "stdout":
            self._add_stdout_handler()
        elif sink_type == "file":
            self._add_file_handler(sink_config)
        elif sink_type == "http":
            self._add_http_handler(sink_config)
            
        # Add additional sinks if configured
        for additional_sink in self.config.get("additional_sinks", []):
            sink_type = additional_sink.get("type")
            if sink_type == "stdout":
                self._add_stdout_handler(additional_sink)
            elif sink_type == "file":
                self._add_file_handler(additional_sink)
            elif sink_type == "http":
                self._add_http_handler(additional_sink)
                
    def _add_stdout_handler(self, config: Dict[str, Any] = None):
        """Add a stdout handler."""
        if config is None:
            config = self.config
            
        handler = logging.StreamHandler()
        if config.get("format", "json") == "json":
            formatter = self._get_json_formatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def _add_file_handler(self, config: Dict[str, Any]):
        """Add a file handler."""
        path = config.get("path")
        if not path:
            self.logger.warning("File path not specified for file log sink")
            return
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        handler = logging.FileHandler(path)
        if config.get("format", "json") == "json":
            formatter = self._get_json_formatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def _add_http_handler(self, config: Dict[str, Any]):
        """Add an HTTP handler (placeholder - would need a custom implementation)."""
        self.logger.warning("HTTP log sink not yet implemented")
        
    def _get_json_formatter(self):
        """Get a JSON formatter for structured logging."""
        return JsonFormatter()
        
    def get_logger(self) -> logging.Logger:
        """Get the configured logger."""
        return self.logger


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    """
    
    def format(self, record):
        """Format the log record as JSON."""
        log_data = {
            "ts": datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).isoformat(),
            "lvl": record.levelname,
            "module": record.name,
            "msg": record.getMessage()
        }
        
        # Add extra fields if available
        if hasattr(record, "event"):
            log_data["event"] = record.event
            
        # Add any other extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "exc_info", "exc_text", "msg", "message", "levelname", "name", "pathname", "filename", "module", "created", "msecs", "relativeCreated", "levelno", "funcName", "lineno", "stack_info", "event"]:
                log_data[key] = value
                
        return json.dumps(log_data)


class ConfigValidator:
    """
    Validates configuration files against the JSON schema.
    """
    
    def __init__(self, schema_path: str = None):
        """Initialize with an optional schema path."""
        self.schema_path = schema_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas",
            "agent_config.schema.json"
        )
        self.schema = self._load_schema()
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema from file."""
        try:
            with open(self.schema_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to load schema from {self.schema_path}: {e}")
            
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a configuration against the schema.
        
        Args:
            config: The configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        validator = jsonschema.Draft7Validator(self.schema)
        errors = list(validator.iter_errors(config))
        
        if not errors:
            return True, []
            
        # Format error messages
        error_messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_messages.append(f"{path}: {error.message}")
            
        return False, error_messages


class AgentFactory:
    """
    Factory class for creating different types of agents.
    """
    
    def __init__(self, event_bus: EventBus, resource_tracker: ResourceTracker, logger: logging.Logger):
        self.event_bus = event_bus
        self.resource_tracker = resource_tracker
        self.logger = logger
        
    async def _build_manifest(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return a manifest describing every agent that will be launched."""
        manifest = []
        idx_counter: Dict[str, int] = {"builder": 0, "operator": 0}
        for entry in config.get("agents", []):
            count = entry.get("count", 1)
            for _ in range(count):
                idx_counter[entry["type"]] += 1
                agent_id = f"{entry['type']}-{idx_counter[entry['type']]}"
                manifest.append(
                    {
                        "agent_id": agent_id,
                        "type": entry["type"],
                        "goal": entry.get("goal", ""),
                    }
                )
        return manifest

    async def create_agents(self, config: Dict[str, Any], run_id: str) -> List[BaseAgent]:
        """
        Create all agents (builders and operators) defined in the unified
        ``agents`` list of the configuration.
        """
        agents_cfg = config.get("agents", [])
        if not agents_cfg:
            self.logger.warning("No agents defined in configuration")
            return []

        manifest = await self._build_manifest(config)
        manifest_iter = iter(manifest)  # to pop IDs in deterministic order

        created: List[BaseAgent] = []
        for entry in agents_cfg:
            # Determine concrete agent class
            agent_cls = BuilderAgent if entry["type"] == "builder" else OperatorAgent
            count = entry.get("count", 1)
            for _ in range(count):
                m = next(manifest_iter)
                cfg_copy = dict(config)
                cfg_copy["run_id"] = run_id
                agent = agent_cls(
                    agent_id=m["agent_id"],
                    config=cfg_copy,
                    event_bus=self.event_bus,
                    logger=self.logger,
                    agent_manifest=manifest,  # <- requires BaseAgent to accept
                )
                created.append(agent)

        return created

    # ------------------------------------------------------------------ #
    # Legacy creators kept (unused) for backward compatibility           #
    # ------------------------------------------------------------------ #
    async def create_builder_agents(self, config: Dict[str, Any], run_id: str) -> List[BuilderAgent]:
        """Create builder agents based on configuration."""
        builder_cfg = config.get("build", {}).get("agents", {})
        models_cfg = builder_cfg.get("models", [])

        agents: List[BuilderAgent] = []
        if models_cfg:
            self.logger.info(
                f"Creating builder agents for {len(models_cfg)} model group(s)"
            )
            for model_index, m_cfg in enumerate(models_cfg, start=1):
                model_agent_count = m_cfg.get("count", 1)
                for agent_idx in range(1, model_agent_count + 1):
                    agent_id = f"builder-{model_index}-{agent_idx}"
                    # Pass run_id into per-agent config copy
                    cfg_copy = dict(config)
                    cfg_copy["run_id"] = run_id
                    agent = BuilderAgent(
                        agent_id=agent_id,
                        config=cfg_copy,
                        event_bus=self.event_bus,
                        logger=self.logger,
                    )
                    agents.append(agent)
        else:
            # Fallback: single model style (legacy)
            count = builder_cfg.get("count", 1)
            self.logger.info(f"Creating {count} builder agent(s)")
            for i in range(1, count + 1):
                agent_id = f"builder-1-{i}"
                cfg_copy = dict(config)
                cfg_copy["run_id"] = run_id
                agents.append(
                    BuilderAgent(
                        agent_id=agent_id,
                        config=cfg_copy,
                        event_bus=self.event_bus,
                        logger=self.logger,
                    )
                )

        return agents
        
    async def create_verifier_agents(self, config: Dict[str, Any], run_id: str) -> List[VerifierAgent]:
        """Create verifier agents based on configuration."""
        verifier_cfg = config.get("verify", {}).get("agents", {})
        models_cfg = verifier_cfg.get("models", [])

        agents: List[VerifierAgent] = []

        if models_cfg:
            self.logger.info(
                f"Creating verifier agents for {len(models_cfg)} model group(s)"
            )
            for model_index, m_cfg in enumerate(models_cfg, start=1):
                model_agent_count = m_cfg.get("count", 1)
                for agent_idx in range(1, model_agent_count + 1):
                    agent_id = f"verifier-{model_index}-{agent_idx}"

                    # Each verifier gets a shallow-copy of the full config with the run-id injected.
                    cfg_copy = dict(config)
                    cfg_copy["run_id"] = run_id

                    agents.append(
                        VerifierAgent(
                            agent_id=agent_id,
                            config=cfg_copy,
                            event_bus=self.event_bus,
                            logger=self.logger,
                        )
                    )
        else:
            # Legacy single-model style
            count = verifier_cfg.get("count", 1)
            self.logger.info(f"Creating {count} verifier agent(s)")
            for i in range(1, count + 1):
                agent_id = f"verifier-1-{i}"
                cfg_copy = dict(config)
                cfg_copy["run_id"] = run_id
                agents.append(
                    VerifierAgent(
                        agent_id=agent_id,
                        config=cfg_copy,
                        event_bus=self.event_bus,
                        logger=self.logger,
                    )
                )

        return agents
        
    async def create_operator_agents(self, config: Dict[str, Any], run_id: str) -> List[OperatorAgent]:
        """Create operator agents based on configuration."""
        operator_config = config.get("operate", {}).get("operator_agents", {})
        count = operator_config.get("count", 1)
        
        self.logger.info(f"Creating {count} operator agent(s)")
        agents = []
        
        for i in range(count):
            agent_id = f"operator-{i+1}"
            agent = OperatorAgent(
                agent_id=agent_id,
                config=config,
                event_bus=self.event_bus,
                logger=self.logger
            )
            agents.append(agent)
            
        return agents


class Orchestrator:
    """
    Main orchestration engine for the Agent Toolkit.
    
    This class manages the lifecycle of agents, coordinates their execution,
    and handles resource constraints and logging.
    """
    
    def __init__(self, config_path: str):
        """Initialize with a configuration file path."""
        self.config_path = config_path
        self.config = self._load_config()
        
        # Set up structured logging
        self.structured_logger = StructuredLogger(self.config)
        self.logger = self.structured_logger.get_logger()
        
        # Generate a unique run ID
        self.run_id = str(uuid.uuid4())
        self.logger.info(f"Initializing orchestrator with run ID: {self.run_id}")
        
        # Set up event bus
        self.event_bus = EventBus(self.logger)
        
        # Set up resource tracker
        self.resource_tracker = ResourceTracker(self.config, self.event_bus, self.logger)
        
        # Set up agent factory
        self.agent_factory = AgentFactory(self.event_bus, self.resource_tracker, self.logger)
        
        # Initialize agent lists
        self.builder_agents: List[BuilderAgent] = []
        self.verifier_agents: List[VerifierAgent] = []
        self.operator_agents: List[OperatorAgent] = []
        
        # Set up event handlers
        self._setup_event_handlers()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        path = Path(self.config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        # Determine file format based on extension
        if path.suffix.lower() in [".yaml", ".yml"]:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
        elif path.suffix.lower() == ".json":
            with open(path, "r") as f:
                config = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")
            
        return config
        
    def _setup_event_handlers(self):
        """Set up handlers for various events."""
        # Resource limit events
        self.event_bus.subscribe(
            EventType.RESOURCE_LIMIT_WARNING,
            self._handle_resource_warning
        )
        self.event_bus.subscribe(
            EventType.RESOURCE_LIMIT_EXCEEDED,
            self._handle_resource_exceeded
        )
        
        # System events
        self.event_bus.subscribe(
            EventType.SYSTEM_SHUTDOWN,
            self._handle_shutdown
        )
        
    async def _handle_resource_warning(self, event: Event):
        """Handle resource warning events."""
        limit_type = event.payload.get("limit_type")
        current = event.payload.get("current")
        limit = event.payload.get("limit")
        percentage = event.payload.get("percentage")
        unit = event.payload.get("unit")
        
        self.logger.warning(
            f"Resource limit warning: {limit_type} usage at {percentage:.1f}% ({current:.2f}/{limit:.2f} {unit})"
        )
        
    async def _handle_resource_exceeded(self, event: Event):
        """Handle resource exceeded events."""
        limit_type = event.payload.get("limit_type")
        current = event.payload.get("current")
        limit = event.payload.get("limit")
        unit = event.payload.get("unit")
        
        self.logger.error(
            f"Resource limit exceeded: {limit_type} usage at {current:.2f}/{limit:.2f} {unit}"
        )
        
        # Initiate graceful shutdown
        await self.shutdown(f"Resource limit exceeded: {limit_type}")
        
    async def _handle_shutdown(self, event: Event):
        """Handle system shutdown events."""
        reason = event.payload.get("reason", "Unknown reason")
        self.logger.info(f"System shutdown initiated: {reason}")
        
    async def validate_config(self) -> bool:
        """Validate the configuration against the schema."""
        validator = ConfigValidator()
        is_valid, errors = validator.validate(self.config)
        
        if is_valid:
            self.logger.info("Configuration validated successfully")
            await self.event_bus.publish(Event(
                type=EventType.CONFIG_VALIDATED,
                run_id=self.run_id,
                payload={"status": "valid"}
            ))
            return True
        else:
            self.logger.error(f"Configuration validation failed: {len(errors)} errors")
            for error in errors:
                self.logger.error(f"  - {error}")
                
            await self.event_bus.publish(Event(
                type=EventType.CONFIG_VALIDATED,
                run_id=self.run_id,
                payload={"status": "invalid", "errors": errors}
            ))
            return False
            
    async def initialize_agents(self):
        """Initialize all agents based on configuration."""
        self.logger.info("Initializing agents")
        
        # Create builder agents
        self.builder_agents = await self.agent_factory.create_builder_agents(
            self.config, self.run_id
        )
        
        # Create verifier agents
        self.verifier_agents = await self.agent_factory.create_verifier_agents(
            self.config, self.run_id
        )
        
        # Create operator agents
        self.operator_agents = await self.agent_factory.create_operator_agents(
            self.config, self.run_id
        )
        
        self.logger.info(
            f"Initialized {len(self.builder_agents)} builder, "
            f"{len(self.verifier_agents)} verifier, and "
            f"{len(self.operator_agents)} operator agents"
        )
        
    async def run_build_phase(self):
        """Run the build phase with builder agents."""
        self.logger.info("Starting build phase")
        await self.event_bus.publish(Event(
            type=EventType.BUILD_START,
            run_id=self.run_id,
            payload={"agent_count": len(self.builder_agents)}
        ))
        
        # Start all builder agents
        tasks = []
        for agent in self.builder_agents:
            tasks.append(agent.start())
            
        # Wait for all agents to complete
        try:
            await asyncio.gather(*tasks)
            self.logger.info("Build phase completed successfully")
            await self.event_bus.publish(Event(
                type=EventType.BUILD_COMPLETED,
                run_id=self.run_id
            ))
            return True
        except Exception as e:
            self.logger.error(f"Build phase failed: {e}")
            await self.event_bus.publish(Event(
                type=EventType.BUILD_FAILED,
                run_id=self.run_id,
                payload={"error": str(e)}
            ))
            return False
            
    async def run_verify_phase(self):
        """Run the verification phase with verifier agents."""
        # Check if verification is enabled
        if not self.verifier_agents:
            self.logger.info("Verification phase skipped (no verifier agents configured)")
            return True
            
        self.logger.info("Starting verification phase")
        await self.event_bus.publish(Event(
            type=EventType.VERIFY_START,
            run_id=self.run_id,
            payload={"agent_count": len(self.verifier_agents)}
        ))
        
        # Get verification strategy
        strategy = self.config.get("verify", {}).get("strategy", "sequential")
        
        if strategy == "sequential":
            return await self._run_sequential_verification()
        elif strategy == "parallel":
            return await self._run_parallel_verification()
        elif strategy == "gated":
            return await self._run_gated_verification()
        else:
            self.logger.warning(f"Unknown verification strategy: {strategy}, using sequential")
            return await self._run_sequential_verification()
            
    async def _run_sequential_verification(self):
        """Run verification agents sequentially."""
        self.logger.info("Using sequential verification strategy")
        
        for agent in self.verifier_agents:
            try:
                await agent.start()
            except Exception as e:
                self.logger.error(f"Verification agent {agent.agent_id} failed: {e}")
                await self.event_bus.publish(Event(
                    type=EventType.VERIFY_FAILED,
                    run_id=self.run_id,
                    agent_id=agent.agent_id,
                    payload={"error": str(e)}
                ))
                return False
                
        self.logger.info("Verification phase completed successfully")
        await self.event_bus.publish(Event(
            type=EventType.VERIFY_COMPLETED,
            run_id=self.run_id
        ))
        return True
        
    async def _run_parallel_verification(self):
        """Run verification agents in parallel."""
        self.logger.info("Using parallel verification strategy")
        
        tasks = []
        for agent in self.verifier_agents:
            tasks.append(agent.start())
            
        try:
            await asyncio.gather(*tasks)
            self.logger.info("Verification phase completed successfully")
            await self.event_bus.publish(Event(
                type=EventType.VERIFY_COMPLETED,
                run_id=self.run_id
            ))
            return True
        except Exception as e:
            self.logger.error(f"Verification phase failed: {e}")
            await self.event_bus.publish(Event(
                type=EventType.VERIFY_FAILED,
                run_id=self.run_id,
                payload={"error": str(e)}
            ))
            return False
            
    async def _run_gated_verification(self):
        """Run verification with gates between tests."""
        self.logger.info("Using gated verification strategy")
        
        # Get test configurations
        tests = self.config.get("verify", {}).get("tests", [])
        
        for i, test_config in enumerate(tests):
            test_type = test_config.get("type", "unknown")
            self.logger.info(f"Running {test_type} test ({i+1}/{len(tests)})")
            
            # Assign test to an agent (round-robin)
            agent_index = i % len(self.verifier_agents)
            agent = self.verifier_agents[agent_index]
            
            try:
                # In a real implementation, we'd pass the test config to the agent
                await agent.start()
            except Exception as e:
                self.logger.error(f"Test {test_type} failed: {e}")
                await self.event_bus.publish(Event(
                    type=EventType.VERIFY_TEST_FAILED,
                    run_id=self.run_id,
                    agent_id=agent.agent_id,
                    payload={"test_type": test_type, "error": str(e)}
                ))
                return False
                
            self.logger.info(f"Test {test_type} passed")
            await self.event_bus.publish(Event(
                type=EventType.VERIFY_TEST_PASSED,
                run_id=self.run_id,
                agent_id=agent.agent_id,
                payload={"test_type": test_type}
            ))
            
        self.logger.info("All verification tests passed")
        await self.event_bus.publish(Event(
            type=EventType.VERIFY_COMPLETED,
            run_id=self.run_id
        ))
        return True
        
    async def run_operate_phase(self):
        """Run the operation phase with operator agents."""
        # Check if operation is enabled
        if not self.operator_agents:
            self.logger.info("Operation phase skipped (no operator agents configured)")
            return True
            
        self.logger.info("Starting operation phase")
        await self.event_bus.publish(Event(
            type=EventType.OPERATE_START,
            run_id=self.run_id,
            payload={"agent_count": len(self.operator_agents)}
        ))
        
        # Start all operator agents
        tasks = []
        for agent in self.operator_agents:
            tasks.append(agent.start())
            
        # Wait for all agents to complete
        try:
            await asyncio.gather(*tasks)
            self.logger.info("Operation phase completed successfully")
            await self.event_bus.publish(Event(
                type=EventType.OPERATE_COMPLETED,
                run_id=self.run_id
            ))
            return True
        except Exception as e:
            self.logger.error(f"Operation phase failed: {e}")
            await self.event_bus.publish(Event(
                type=EventType.OPERATE_FAILED,
                run_id=self.run_id,
                payload={"error": str(e)}
            ))
            return False
            
    async def run(self):
        """Run the full orchestration process."""
        self.logger.info(f"Starting Agent Toolkit run: {self.run_id}")
        
        # Start event processing
        event_processor_task = asyncio.create_task(self.event_bus.process_events())
        
        # Publish system start event
        await self.event_bus.publish(Event(
            type=EventType.SYSTEM_START,
            run_id=self.run_id,
            payload={"config_path": self.config_path}
        ))
        
        # Validate configuration
        if not await self.validate_config():
            self.logger.error("Configuration validation failed, aborting")
            await self.shutdown("Configuration validation failed")
            return False
            
        # Initialize agents
        await self.initialize_agents()
        
        # Run build phase
        if not await self.run_build_phase():
            self.logger.error("Build phase failed, aborting")
            await self.shutdown("Build phase failed")
            return False
            
        # Run verification phase
        if not await self.run_verify_phase():
            self.logger.error("Verification phase failed, aborting")
            await self.shutdown("Verification phase failed")
            return False
            
        # Run operation phase
        if not await self.run_operate_phase():
            self.logger.error("Operation phase failed, aborting")
            await self.shutdown("Operation phase failed")
            return False
            
        # Successful completion
        self.logger.info("Agent Toolkit run completed successfully")
        
        # Print resource usage summary
        summary = self.resource_tracker.get_summary()
        self.logger.info(
            f"Resource usage summary: {summary['elapsed_time']['minutes']:.2f} minutes, "
            f"${summary['cost']['usd']:.2f}, {summary['tokens']['total']} tokens"
        )
        
        # Shutdown
        await self.shutdown("Run completed successfully")
        
        # Wait for event processor to complete
        await event_processor_task
        
        return True
        
    async def shutdown(self, reason: str = "Unknown reason"):
        """Shutdown the orchestrator and all agents."""
        self.logger.info(f"Shutting down orchestrator: {reason}")

        # ------------------------------------------------------------------ #
        # 1) Allow in-flight events a moment to be processed                 #
        # ------------------------------------------------------------------ #
        DRAIN_PAUSE_SEC = 0.5
        await asyncio.sleep(DRAIN_PAUSE_SEC)

        # ------------------------------------------------------------------ #
        # 2) Wait for the EventBus queue to drain before we stop agents      #
        # ------------------------------------------------------------------ #
        QUEUE_DRAIN_TIMEOUT = 5.0  # seconds
        self.logger.debug(
            "Waiting for event queue to empty before stopping agents...",
            extra={"timeout_sec": QUEUE_DRAIN_TIMEOUT},
        )
        try:
            await asyncio.wait_for(self.event_bus.queue.join(), timeout=QUEUE_DRAIN_TIMEOUT)
            self.logger.debug("Event queue drained.")
        except asyncio.TimeoutError:
            self.logger.warning(
                "Timed-out waiting for event queue to drain; proceeding with shutdown."
            )

        # ------------------------------------------------------------------ #
        # 3) Stop all agents (they might still publish a few final events)   #
        # ------------------------------------------------------------------ #
        for agent in self.builder_agents + self.verifier_agents + self.operator_agents:
            try:
                await agent.stop()
            except Exception as e:
                self.logger.error(f"Error stopping agent {agent.agent_id}: {e}")

        # Small pause so any events emitted during `.stop()` get queued
        await asyncio.sleep(0.2)

        # Drain again quickly
        try:
            await asyncio.wait_for(self.event_bus.queue.join(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # ------------------------------------------------------------------ #
        # 4) Emit final SYSTEM_SHUTDOWN event                                #
        # ------------------------------------------------------------------ #
        await self.event_bus.publish(
            Event(
                type=EventType.SYSTEM_SHUTDOWN,
                run_id=self.run_id,
                payload={"reason": reason},
            )
        )

        self.logger.info("Shutdown sequence complete.")


async def run_orchestrator(config_path: str) -> bool:
    """Run the orchestrator with the given configuration file."""
    orchestrator = Orchestrator(config_path)
    return await orchestrator.run()


def main():
    """Command-line entry point for the orchestrator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Toolkit Orchestrator")
    parser.add_argument("config", help="Path to configuration file (YAML or JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Run the orchestrator
    try:
        asyncio.run(run_orchestrator(args.config))
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
