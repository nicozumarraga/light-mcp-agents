"""
Configuration module for the MCP agent application.
"""

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


class MCPServerConfig:
    """Configuration for an MCP server."""

    def __init__(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        transport: str = "stdio",
    ):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.transport = transport

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'MCPServerConfig':
        """Create a server config from a dictionary."""
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            transport=data.get("transport", "stdio"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "transport": self.transport,
        }


class Config:
    """Application configuration."""

    def __init__(self):
        """Initialize configuration."""
        # Load environment variables
        load_dotenv()

        # LLM configuration
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()

        # Server configurations
        self.server_configs: Dict[str, MCPServerConfig] = {}

    def load_server_configs(self, file_path: str) -> None:
        """Load server configurations from a JSON file."""
        with open(file_path, "r") as f:
            data = json.load(f)

        if "mcpServers" in data:
            for name, server_data in data["mcpServers"].items():
                self.server_configs[name] = MCPServerConfig.from_dict(name, server_data)

    def validate(self) -> List[str]:
        """Validate the configuration and return a list of validation errors."""
        errors = []

        if not self.llm_api_key:
            errors.append("LLM_API_KEY not found in environment variables")

        if not self.llm_provider:
            errors.append("LLM_PROVIDER not found in environment variables")

        if self.llm_provider not in ["groq", "openai", "anthropic"]:
            errors.append(f"Unsupported LLM provider: {self.llm_provider}")

        if not self.server_configs:
            errors.append("No server configurations found")

        for name, config in self.server_configs.items():
            if not config.command:
                errors.append(f"Server {name} has no command specified")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "llm_provider": self.llm_provider,
            "mcpServers": {
                name: config.to_dict()
                for name, config in self.server_configs.items()
            }
        }


def load_config(config_path: str = "servers_config.json") -> Config:
    """Load and validate configuration."""
    config = Config()
    config.load_server_configs(config_path)

    errors = config.validate()
    if errors:
        for error in errors:
            print(f"Configuration error: {error}")
        raise ValueError("Invalid configuration")

    return config
