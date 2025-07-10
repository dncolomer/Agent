#!/usr/bin/env python3
"""
Agent Collaboration Visualizer

This module provides visualization capabilities for agent collaboration patterns.
It analyzes log files to extract agent interactions and generates visual
representations of how agents collaborated during a run.

Features:
- Network graph visualization showing agent communication patterns
- Timeline visualization showing temporal sequence of interactions
- Integration with the orchestration system for automatic visualization
- Configurable via the YAML configuration file
"""

import asyncio
import json
import logging
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import networkx as nx
    from matplotlib.lines import Line2D
except ImportError:
    import subprocess
    import sys
    print("Required visualization libraries not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "matplotlib", "networkx"])
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import networkx as nx
    from matplotlib.lines import Line2D


class Visualizer:
    """
    Agent collaboration visualizer.
    
    This class analyzes log files to extract agent interactions and
    generates visualizations showing collaboration patterns.
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initialize the visualizer with configuration.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        
        # Extract visualization configuration
        self.viz_config = config.get("visualization", {})
        self.enabled = self.viz_config.get("enabled", False)
        self.output_dir = self.viz_config.get("output_directory", "visualizations")
        self.view_type = self.viz_config.get("type", "both")
        self.format = self.viz_config.get("format", "png")
        self.dpi = self.viz_config.get("dpi", 300)
        
        # Create output directory if it doesn't exist
        if self.enabled:
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f"Visualization enabled, output directory: {self.output_dir}")
    
    async def visualize_run(self, run_id: str) -> bool:
        """
        Generate visualizations for a specific run.
        
        Args:
            run_id: Unique identifier for the run
            
        Returns:
            True if visualization was successful, False otherwise
        """
        if not self.enabled:
            self.logger.info("Visualization is disabled in configuration")
            return False
        
        # Find the log file for this run
        log_path = self._find_log_file(run_id)
        if not log_path:
            self.logger.error(f"Could not find log file for run {run_id}")
            return False
        
        self.logger.info(f"Generating visualizations for run {run_id} using log file {log_path}")
        
        try:
            # Parse the log file
            log_entries = self._parse_log_file(log_path)
            
            # Extract agent interactions
            interactions, agent_types, message_counts, timeline_data = self._extract_agent_interactions(log_entries)
            
            if not interactions:
                self.logger.warning("No agent interactions found in the log file")
                return False
            
            # Create visualizations based on view type
            if self.view_type in ["network", "both"]:
                self._create_network_graph(interactions, agent_types, message_counts, run_id)
                
            if self.view_type in ["timeline", "both"]:
                self._create_timeline_visualization(timeline_data, agent_types, run_id)
                
            self.logger.info(f"Visualizations generated successfully in {self.output_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating visualizations: {e}")
            return False
    
    def _find_log_file(self, run_id: str) -> Optional[str]:
        """
        Find the log file for a specific run.
        
        Args:
            run_id: Unique identifier for the run
            
        Returns:
            Path to the log file, or None if not found
        """
        # Check logging configuration
        log_config = self.config.get("logging", {})
        sink_config = log_config.get("sink", {})
        
        if sink_config.get("type") == "file":
            log_path = sink_config.get("path")
            if log_path and run_id in log_path:
                return log_path
        
        # If not found in primary sink, check additional sinks
        for sink in log_config.get("additional_sinks", []):
            if sink.get("type") == "file":
                log_path = sink.get("path")
                if log_path and run_id in log_path:
                    return log_path
        
        # If not found in configuration, look in logs directory
        logs_dir = Path("logs")
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.ndjson"):
                if run_id in log_file.name:
                    return str(log_file)
        
        return None
    
    def _parse_log_file(self, log_path: str) -> List[Dict]:
        """
        Parse an NDJSON log file into a list of log entries.
        
        Args:
            log_path: Path to the NDJSON log file
            
        Returns:
            List of parsed log entries as dictionaries
        """
        log_entries = []
        try:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        log_entries.append(entry)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not parse log line: {line[:100]}...")
        except FileNotFoundError:
            self.logger.error(f"Log file not found: {log_path}")
            return []
        except Exception as e:
            self.logger.error(f"Error reading log file: {e}")
            return []
            
        self.logger.info(f"Parsed {len(log_entries)} log entries from {log_path}")
        return log_entries
    
    def _extract_agent_interactions(self, log_entries: List[Dict]) -> Tuple[Dict, Dict, Dict, Dict]:
        """
        Extract agent interactions from log entries.
        
        Args:
            log_entries: List of parsed log entries
            
        Returns:
            Tuple of (interactions, agent_types, message_counts, timeline_data)
            - interactions: Dict mapping (source, target) to count
            - agent_types: Dict mapping agent_id to type (builder/operator)
            - message_counts: Dict mapping (source, target) to Counter of message types
            - timeline_data: Dict mapping timestamp to list of interactions
        """
        interactions = defaultdict(int)
        agent_types = {}
        message_counts = defaultdict(Counter)
        timeline_data = defaultdict(list)
        
        # First pass: identify agent types
        for entry in log_entries:
            if "agent_type" in entry and "agent_id" in entry:
                agent_types[entry["agent_id"]] = entry["agent_type"]
                
            # Also check payload for agent type information
            if "payload" in entry and isinstance(entry["payload"], dict):
                payload = entry["payload"]
                if "agent_type" in payload and "from" in payload:
                    agent_types[payload["from"]] = payload["agent_type"]
        
        # Second pass: extract interactions
        for entry in log_entries:
            timestamp = entry.get("ts")
            if not timestamp:
                continue
                
            # Convert timestamp to datetime
            try:
                dt = datetime.fromisoformat(timestamp)
            except ValueError:
                # Try to handle non-standard format
                try:
                    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f%z")
                except ValueError:
                    continue
            
            # Check for agent messages
            if entry.get("msg", "").startswith("Agent") and "received message" in entry.get("msg", ""):
                agent_id = entry.get("agent_id")
                if not agent_id:
                    # Try to extract from message
                    msg_parts = entry.get("msg", "").split()
                    if len(msg_parts) > 1:
                        agent_id = msg_parts[1]
                
                payload = entry.get("payload", {})
                if isinstance(payload, dict) and "from" in payload:
                    sender = payload.get("from")
                    action = payload.get("action", "unknown")
                    
                    if sender and agent_id and sender != agent_id:
                        # Record interaction
                        interactions[(sender, agent_id)] += 1
                        message_counts[(sender, agent_id)][action] += 1
                        
                        # Record for timeline
                        timeline_data[dt].append({
                            "from": sender,
                            "to": agent_id,
                            "action": action,
                            "message": payload.get("message", "")[:50]  # Truncate long messages
                        })
            
            # Check for direct agent-to-agent communication
            elif entry.get("msg", "").startswith("Agent") and "sending message to" in entry.get("msg", ""):
                sender = entry.get("agent_id")
                to = entry.get("to")
                if sender and to and sender != to:
                    action = entry.get("payload", {}).get("action", "unknown")
                    
                    # Record interaction
                    interactions[(sender, to)] += 1
                    message_counts[(sender, to)][action] += 1
                    
                    # Record for timeline
                    timeline_data[dt].append({
                        "from": sender,
                        "to": to,
                        "action": action,
                        "message": entry.get("payload", {}).get("message", "")[:50]  # Truncate long messages
                    })
        
        # Ensure all agents have a type
        for source, target in interactions.keys():
            if source not in agent_types:
                # Try to infer type from ID
                if source.startswith("builder"):
                    agent_types[source] = "builder"
                elif source.startswith("operator"):
                    agent_types[source] = "operator"
                else:
                    agent_types[source] = "unknown"
                    
            if target not in agent_types:
                # Try to infer type from ID
                if target.startswith("builder"):
                    agent_types[target] = "builder"
                elif target.startswith("operator"):
                    agent_types[target] = "operator"
                else:
                    agent_types[target] = "unknown"
        
        return interactions, agent_types, message_counts, timeline_data
    
    def _create_network_graph(self, interactions: Dict, agent_types: Dict, 
                             message_counts: Dict, run_id: str) -> None:
        """
        Create and save a network graph of agent interactions.
        
        Args:
            interactions: Dict mapping (source, target) to interaction count
            agent_types: Dict mapping agent_id to type
            message_counts: Dict mapping (source, target) to Counter of message types
            run_id: Unique identifier for the run
        """
        G = nx.DiGraph()
        
        # Add nodes with attributes
        for agent_id, agent_type in agent_types.items():
            G.add_node(agent_id, type=agent_type)
        
        # Add edges with attributes
        for (source, target), count in interactions.items():
            message_types = message_counts[(source, target)]
            G.add_edge(source, target, weight=count, messages=dict(message_types))
        
        # Create the figure
        plt.figure(figsize=(12, 10))
        
        # Define node colors based on agent type
        node_colors = []
        for node in G.nodes():
            if agent_types[node] == "builder":
                node_colors.append("skyblue")
            elif agent_types[node] == "operator":
                node_colors.append("lightgreen")
            else:
                node_colors.append("lightgray")
        
        # Define edge widths based on interaction count
        edge_widths = [G[u][v]['weight'] for u, v in G.edges()]
        max_width = max(edge_widths) if edge_widths else 1
        edge_widths = [1 + 5 * (w / max_width) for w in edge_widths]
        
        # Define layout
        pos = nx.spring_layout(G, seed=42)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=700, alpha=0.8)
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.6, edge_color="gray", 
                              arrowsize=20, connectionstyle='arc3,rad=0.1')
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        # Add edge labels (message counts)
        edge_labels = {(u, v): f"{G[u][v]['weight']} msgs" for u, v in G.edges()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        # Add legend
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='skyblue', markersize=15, label='Builder Agent'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen', markersize=15, label='Operator Agent')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        # Set title and layout
        plt.title('Agent Collaboration Network', fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        
        # Save the figure
        output_file = os.path.join(self.output_dir, f"agent_collaboration_network_{run_id}.{self.format}")
        plt.savefig(output_file, dpi=self.dpi)
        self.logger.info(f"Network graph saved to {output_file}")
        
        # Close the figure to free memory
        plt.close()
    
    def _create_timeline_visualization(self, timeline_data: Dict, agent_types: Dict, run_id: str) -> None:
        """
        Create and save a timeline visualization of agent interactions.
        
        Args:
            timeline_data: Dict mapping timestamp to list of interactions
            agent_types: Dict mapping agent_id to type
            run_id: Unique identifier for the run
        """
        # Sort timeline data by timestamp
        sorted_times = sorted(timeline_data.keys())
        if not sorted_times:
            self.logger.warning("No timeline data available for visualization")
            return
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Track y positions for each agent
        agent_positions = {}
        next_pos = 1
        
        # Get all agents involved
        all_agents = set()
        for interactions in timeline_data.values():
            for interaction in interactions:
                all_agents.add(interaction["from"])
                all_agents.add(interaction["to"])
        
        # Assign positions
        for agent in sorted(all_agents):
            agent_positions[agent] = next_pos
            next_pos += 1
        
        # Draw agent labels
        for agent, pos in agent_positions.items():
            agent_type = agent_types.get(agent, "unknown")
            color = "skyblue" if agent_type == "builder" else "lightgreen" if agent_type == "operator" else "lightgray"
            ax.text(-0.01, pos, agent, fontsize=10, ha="right", va="center", 
                    bbox=dict(facecolor=color, alpha=0.5, boxstyle="round,pad=0.5"))
        
        # Draw interactions
        for dt, interactions in sorted(timeline_data.items()):
            for interaction in interactions:
                source = interaction["from"]
                target = interaction["to"]
                action = interaction["action"]
                
                # Skip if either agent is not in our position map
                if source not in agent_positions or target not in agent_positions:
                    continue
                    
                source_pos = agent_positions[source]
                target_pos = agent_positions[target]
                
                # Determine color based on action type
                if action == "announce":
                    color = "blue"
                elif action == "acknowledge":
                    color = "green"
                elif action == "plan_update":
                    color = "purple"
                elif action == "task_update":
                    color = "orange"
                elif action == "help_request":
                    color = "red"
                elif action == "help_response":
                    color = "brown"
                else:
                    color = "gray"
                
                # Draw arrow from source to target
                ax.annotate("", 
                          xy=(mdates.date2num(dt), target_pos), 
                          xytext=(mdates.date2num(dt), source_pos),
                          arrowprops=dict(arrowstyle="->", color=color, lw=1.5, alpha=0.7))
                
                # Add small marker at the target point
                ax.plot(mdates.date2num(dt), target_pos, 'o', color=color, markersize=4)
        
        # Configure x-axis to show time
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()
        
        # Configure y-axis
        ax.set_yticks([])
        ax.set_ylim(0, next_pos)
        
        # Add legend for message types
        legend_elements = [
            Line2D([0], [0], color='blue', lw=2, label='Announce'),
            Line2D([0], [0], color='green', lw=2, label='Acknowledge'),
            Line2D([0], [0], color='purple', lw=2, label='Plan Update'),
            Line2D([0], [0], color='orange', lw=2, label='Task Update'),
            Line2D([0], [0], color='red', lw=2, label='Help Request'),
            Line2D([0], [0], color='brown', lw=2, label='Help Response'),
            Line2D([0], [0], color='gray', lw=2, label='Other')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Set title and labels
        plt.title('Agent Interaction Timeline', fontsize=16)
        plt.xlabel('Time', fontsize=12)
        plt.grid(True, axis='x', alpha=0.3)
        
        # Save the figure
        output_file = os.path.join(self.output_dir, f"agent_interaction_timeline_{run_id}.{self.format}")
        plt.savefig(output_file, dpi=self.dpi)
        self.logger.info(f"Timeline visualization saved to {output_file}")
        
        # Close the figure to free memory
        plt.close()
    
    def generate_summary(self, interactions: Dict, agent_types: Dict, message_counts: Dict) -> str:
        """
        Generate a textual summary of agent interactions.
        
        Args:
            interactions: Dict mapping (source, target) to interaction count
            agent_types: Dict mapping agent_id to type
            message_counts: Dict mapping (source, target) to Counter of message types
            
        Returns:
            A formatted string with the interaction summary
        """
        summary = ["Agent Collaboration Summary", "========================="]
        
        # Total interactions
        total_messages = sum(interactions.values())
        summary.append(f"Total interactions: {total_messages} messages between {len(agent_types)} agents")
        
        # Agent types summary
        builder_count = sum(1 for t in agent_types.values() if t == "builder")
        operator_count = sum(1 for t in agent_types.values() if t == "operator")
        summary.append(f"Agent composition: {builder_count} builders, {operator_count} operators")
        
        # Top interactions
        summary.append("\nTop Agent Interactions:")
        for (source, target), count in sorted(interactions.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary.append(f"  {source} → {target}: {count} messages")
            message_types = message_counts[(source, target)]
            for msg_type, msg_count in message_types.most_common(3):
                summary.append(f"    - {msg_type}: {msg_count}")
                
        return "\n".join(summary)


# Integration functions for use with the orchestrator

async def generate_visualizations(config: Dict[str, Any], logger: logging.Logger, run_id: str) -> bool:
    """
    Generate visualizations for a completed run.
    
    This function is designed to be called from the orchestrator at the
    end of a run to generate visualizations of agent collaboration.
    
    Args:
        config: Configuration dictionary
        logger: Logger instance
        run_id: Unique identifier for the run
        
    Returns:
        True if visualization was successful, False otherwise
    """
    visualizer = Visualizer(config, logger)
    return await visualizer.visualize_run(run_id)
