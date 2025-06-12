#!/usr/bin/env python3
"""
Setup script for the Agent Toolkit package.

This script allows the package to be installed using pip.
"""

import os
from setuptools import setup, find_packages

# Get the long description from the README file
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Get version from __init__.py
with open(os.path.join(here, "agent_toolkit", "__init__.py"), encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"\'')
            break
    else:
        version = "0.1.0"  # Default if not found

# Define required dependencies
install_requires = [
    "pydantic>=2.4.2",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "jsonschema>=4.17.0",
    "click>=8.1.7",
    "pyyaml>=6.0.1",
    "tenacity>=8.2.3",
    "loguru>=0.7.0",
    "aiohttp>=3.8.5",
    "asyncio>=3.4.3",
]

# Define development dependencies
dev_requires = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.7.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.5.1",
]

setup(
    name="agent-toolkit",
    version=version,
    description="A configuration-driven multi-agent orchestration system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dncolomer/Agent",
    author="Agent Toolkit Team",
    author_email="info@agent-toolkit.org",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="agent, llm, orchestration, automation",
    packages=find_packages(exclude=["tests", "examples"]),
    python_requires=">=3.10",
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
    },
    package_data={
        "agent_toolkit": ["schemas/*.json"],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "agentctl=agent_toolkit.cli:cli",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/dncolomer/Agent/issues",
        "Source": "https://github.com/dncolomer/Agent",
    },
)
