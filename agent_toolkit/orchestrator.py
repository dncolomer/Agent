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
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import jsonschema
import yaml
from pydantic import BaseModel, Field, ValidationError

# Import agent types (to be implemented in separate files)
# from agent_toolkit.agents.base_agent import BaseAgent
# from agent_toolkit.agents.builder import BuilderAgent
# from agent_toolkit.agents.verifier import VerifierAgent
# from agent_toolkit.agents.operator import OperatorAgent

# Temporarily define placeholder classes until the actual implementations are created
class BaseAgent:
    """Placeholder for the BaseAgent class."""
    def __init__(self, agent_id: str, config: Dict[str, Any], event_bus: 'EventBus', logger: logging.Logger):
        self.agent_id = agent_id
        self.config = config
        self.event_bus = event_bus
        self.logger = logger
        
    async def start(self):
        """Start the agent's execution."""
        pass
        
    async def stop(self):
        """Stop the agent's execution."""
        pass


class BuilderAgent(BaseAgent):
    """Placeholder for the BuilderAgent class."""
    pass


class VerifierAgent(BaseAgent):
    """Placeholder for the VerifierAgent class."""
    pass


class OperatorAgent(BaseAgent):
    """Placeholder for the OperatorAgent class."""
    pass


class EventType(str, Enum):
    """Event types for the event bus."""
    # System events
    SYSTEM_START = "system.start"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_LOADED = "config.loaded"
    CONFIG_VALIDATED = "config.validated"
    
    # Build events
    BUILD_START = "build.start"
    BUILD_STEP_START = "build.step.start"
    BUILD_STEP_COMPLETED = "build.step.completed"
    BUILD_STEP_FAILED = "build.step.failed"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"
    
    # Verification events
    VERIFY_START = "verify.start"
    VERIFY_TEST_START = "verify.test.start"
    VERIFY_TEST_PASSED = "verify.test.passed"
    VERIFY_TEST_FAILED = "verify.test.failed"
    VERIFY_COMPLETED = "verify.completed"
    VERIFY_FAILED = "verify.failed"
    
    # Operation events
    OPERATE_START = "operate.start"
    OPERATE_ACTION = "operate.action"
    OPERATE_ALERT = "operate.alert"
    OPERATE_COMPLETED = "operate.completed"
    OPERATE_FAILED = "operate.failed"
    
    # Resource events
    RESOURCE_LIMIT_WARNING = "resource.limit.warning"
    RESOURCE_LIMIT_EXCEEDED = "resource.limit.exceeded"


class Event(BaseModel):
    """Event model for the event bus."""
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    agent_id: Optional[str] = None
    run_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventBus:
    """
    Simple in-process event bus for agent communication.
    
    This class provides a publish-subscribe mechanism for agents to communicate
    with each other and with the orchestration engine.
    """
    
    def __init__(self, logger: logging.Logger):
        self.subscribers: Dict[EventType, Set[callable]] = {}
        self.queue = asyncio.Queue()
        self.logger = logger
        
    def subscribe(self, event_type: EventType, callback: callable):
        """Subscribe to an event type with a callback function."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(callback)
        
    def unsubscribe(self, event_type: EventType, callback: callable):
        """Unsubscribe from an event type."""
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        self.logger.debug(f"Event published: {event.type}", extra={"event": event.dict()})
        await self.queue.put(event)
        
    async def process_events(self):
        """Process events from the queue."""
        while True:
            event = await self.queue.get()
            
            # Call subscribers for this event type
            if event.type in self.subscribers:
                for callback in self.subscribers[event.type]:
                    try:
                        await callback(event)
                    except Exception as e:
                        self.logger.error(f"Error in event subscriber: {e}", 
                                         extra={"event_type": event.type, "error": str(e)})
            
            # Mark task as done
            self.queue.task_done()
            
            # Special handling for shutdown event
            if event.type == EventType.SYSTEM_SHUTDOWN:
                # Wait for any remaining events to be processed
                if self.queue.empty():
                    break


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
        self.max_cost_usd = config.get("build", {}).get("agents", {}).get("max_cost_usd", float("inf"))
        self.max_runtime_min = config.get("build", {}).get("agents", {}).get("max_runtime_min", float("inf"))
        
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
        
    async def create_builder_agents(self, config: Dict[str, Any], run_id: str) -> List[BuilderAgent]:
        """Create builder agents based on configuration."""
        builder_config = config.get("build", {}).get("agents", {})
        count = builder_config.get("count", 1)
        
        self.logger.info(f"Creating {count} builder agent(s)")
        agents = []
        
        for i in range(count):
            agent_id = f"builder-{i+1}"
            agent = BuilderAgent(
                agent_id=agent_id,
                config=config,
                event_bus=self.event_bus,
                logger=self.logger
            )
            agents.append(agent)
            
        return agents
        
    async def create_verifier_agents(self, config: Dict[str, Any], run_id: str) -> List[VerifierAgent]:
        """Create verifier agents based on configuration."""
        verifier_config = config.get("verify", {}).get("agents", {})
        count = verifier_config.get("count", 1)
        
        self.logger.info(f"Creating {count} verifier agent(s)")
        agents = []
        
        for i in range(count):
            agent_id = f"verifier-{i+1}"
            agent = VerifierAgent(
                agent_id=agent_id,
                config=config,
                event_bus=self.event_bus,
                logger=self.logger
            )
            agents.append(agent)
            
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
        
        # Stop all agents
        for agent in self.builder_agents + self.verifier_agents + self.operator_agents:
            try:
                await agent.stop()
            except Exception as e:
                self.logger.error(f"Error stopping agent {agent.agent_id}: {e}")
                
        # Publish shutdown event
        await self.event_bus.publish(Event(
            type=EventType.SYSTEM_SHUTDOWN,
            run_id=self.run_id,
            payload={"reason": reason}
        ))


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
