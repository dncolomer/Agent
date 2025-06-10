#!/usr/bin/env python3
"""
Project Executor - File System Operations Module

This module handles project execution tasks like creating files,
modifying files, and running commands. It provides a safe interface
for interacting with the file system.
"""

import os
import logging
import subprocess
from typing import List, Dict, Optional, Union, Tuple
import shutil
import tempfile
import re


class ProjectExecutor:
    """
    ProjectExecutor handles file system operations for the agent.
    
    This class provides methods for creating files, modifying existing files,
    and executing shell commands in a controlled environment.
    """
    
    def __init__(self, project_dir: str):
        """
        Initialize the ProjectExecutor.
        
        Args:
            project_dir: Directory where the project files will be stored
        """
        self.logger = logging.getLogger(__name__)
        self.project_dir = os.path.abspath(project_dir)
        
        # Create project directory if it doesn't exist
        os.makedirs(self.project_dir, exist_ok=True)
        
        self.logger.info(f"ProjectExecutor initialized with directory: {self.project_dir}")
    
    def list_files(self, include_dirs: bool = True) -> List[str]:
        """
        List all files in the project directory.
        
        Args:
            include_dirs: Whether to include directories in the result
            
        Returns:
            List of relative paths to files in the project directory
        """
        result = []
        
        for root, dirs, files in os.walk(self.project_dir):
            # Get the relative path from the project directory
            rel_root = os.path.relpath(root, self.project_dir)
            
            # Add directories if requested
            if include_dirs and rel_root != '.':
                result.append(rel_root)
            
            # Add files with their relative paths
            for file in files:
                if rel_root == '.':
                    result.append(file)
                else:
                    result.append(os.path.join(rel_root, file))
        
        return result
    
    def create_file(self, file_path: str, content: str) -> bool:
        """
        Create a new file with the specified content.
        
        Args:
            file_path: Path to the file (relative to project directory)
            content: Content to write to the file
            
        Returns:
            True if the file was created successfully, False otherwise
        """
        abs_path = os.path.join(self.project_dir, file_path)
        
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            # Write the file
            with open(abs_path, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Created file: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating file {file_path}: {e}")
            return False
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read the content of a file.
        
        Args:
            file_path: Path to the file (relative to project directory)
            
        Returns:
            Content of the file as a string, or None if the file doesn't exist
        """
        abs_path = os.path.join(self.project_dir, file_path)
        
        if not os.path.exists(abs_path):
            self.logger.warning(f"File not found: {file_path}")
            return None
        
        try:
            with open(abs_path, 'r') as f:
                content = f.read()
            
            self.logger.debug(f"Read file: {file_path}")
            return content
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def modify_file(self, file_path: str, new_content: str) -> bool:
        """
        Modify an existing file with new content.
        
        Args:
            file_path: Path to the file (relative to project directory)
            new_content: New content for the file
            
        Returns:
            True if the file was modified successfully, False otherwise
        """
        abs_path = os.path.join(self.project_dir, file_path)
        
        if not os.path.exists(abs_path):
            self.logger.warning(f"File not found for modification: {file_path}")
            return False
        
        try:
            # Create a backup of the original file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                with open(abs_path, 'rb') as src:
                    shutil.copyfileobj(src, tmp)
                backup_path = tmp.name
            
            # Write the new content
            with open(abs_path, 'w') as f:
                f.write(new_content)
            
            # Remove the backup if everything went well
            os.unlink(backup_path)
            
            self.logger.info(f"Modified file: {file_path}")
            return True
        except Exception as e:
            # Restore from backup if there was an error
            if 'backup_path' in locals():
                try:
                    shutil.copy(backup_path, abs_path)
                    os.unlink(backup_path)
                except Exception as restore_error:
                    self.logger.error(f"Error restoring backup: {restore_error}")
            
            self.logger.error(f"Error modifying file {file_path}: {e}")
            return False
    
    def apply_patch(self, file_path: str, patch_operations: List[Dict]) -> bool:
        """
        Apply a series of patch operations to a file.
        
        Args:
            file_path: Path to the file (relative to project directory)
            patch_operations: List of patch operations, each containing:
                - operation: 'insert', 'replace', or 'delete'
                - line_number: Line number to operate on (1-based)
                - content: Content to insert or replace with (for insert/replace)
                - lines: Number of lines to delete/replace (for delete/replace)
            
        Returns:
            True if the patch was applied successfully, False otherwise
        """
        content = self.read_file(file_path)
        if content is None:
            return False
        
        lines = content.splitlines()
        
        # Sort operations in reverse order of line number to avoid shifting issues
        sorted_ops = sorted(patch_operations, key=lambda op: op.get('line_number', 0), reverse=True)
        
        for op in sorted_ops:
            operation = op.get('operation')
            line_num = op.get('line_number', 0)
            
            # Convert to 0-based indexing
            if line_num > 0:
                line_num -= 1
            
            if operation == 'insert' and 0 <= line_num <= len(lines):
                lines.insert(line_num, op.get('content', ''))
            
            elif operation == 'replace' and 0 <= line_num < len(lines):
                num_lines = op.get('lines', 1)
                replacement = op.get('content', '').splitlines()
                lines[line_num:line_num + num_lines] = replacement
            
            elif operation == 'delete' and 0 <= line_num < len(lines):
                num_lines = op.get('lines', 1)
                del lines[line_num:line_num + num_lines]
            
            else:
                self.logger.warning(f"Invalid patch operation: {op}")
        
        # Join lines back into content
        new_content = '\n'.join(lines)
        if lines and not content.endswith('\n'):
            new_content += '\n'
        
        return self.modify_file(file_path, new_content)
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from the project.
        
        Args:
            file_path: Path to the file (relative to project directory)
            
        Returns:
            True if the file was deleted successfully, False otherwise
        """
        abs_path = os.path.join(self.project_dir, file_path)
        
        if not os.path.exists(abs_path):
            self.logger.warning(f"File not found for deletion: {file_path}")
            return False
        
        try:
            os.remove(abs_path)
            self.logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def run_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Run a shell command in the project directory.
        
        Args:
            command: Command to run
            timeout: Maximum time to wait for the command to complete (seconds)
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        # Check for potentially dangerous commands
        dangerous_patterns = [
            r'rm\s+-rf\s+[/~]',  # rm -rf / or rm -rf ~
            r'dd\s+.*\s+of=/dev/',  # dd to device files
            r'>\s+/dev/sd[a-z]',  # redirect to disk devices
            r'mkfs',  # format filesystems
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                self.logger.error(f"Potentially dangerous command rejected: {command}")
                return (1, '', 'Command rejected for security reasons')
        
        self.logger.info(f"Running command: {command}")
        
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            self.logger.debug(f"Command completed with return code: {process.returncode}")
            return (process.returncode, stdout, stderr)
        
        except subprocess.TimeoutExpired:
            process.kill()
            self.logger.error(f"Command timed out after {timeout} seconds: {command}")
            return (1, '', f'Command timed out after {timeout} seconds')
        
        except Exception as e:
            self.logger.error(f"Error running command: {e}")
            return (1, '', str(e))
    
    def create_directory(self, dir_path: str) -> bool:
        """
        Create a directory in the project.
        
        Args:
            dir_path: Path to the directory (relative to project directory)
            
        Returns:
            True if the directory was created successfully, False otherwise
        """
        abs_path = os.path.join(self.project_dir, dir_path)
        
        try:
            os.makedirs(abs_path, exist_ok=True)
            self.logger.info(f"Created directory: {dir_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {dir_path}: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in the project.
        
        Args:
            file_path: Path to the file (relative to project directory)
            
        Returns:
            True if the file exists, False otherwise
        """
        abs_path = os.path.join(self.project_dir, file_path)
        return os.path.isfile(abs_path)
    
    def directory_exists(self, dir_path: str) -> bool:
        """
        Check if a directory exists in the project.
        
        Args:
            dir_path: Path to the directory (relative to project directory)
            
        Returns:
            True if the directory exists, False otherwise
        """
        abs_path = os.path.join(self.project_dir, dir_path)
        return os.path.isdir(abs_path)
