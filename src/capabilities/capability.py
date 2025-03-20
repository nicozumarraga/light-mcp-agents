"""
Capability classes for exposing agent reasoning as tools.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.types import Tool as MCPTool


class AgentCapability:
    """
    Represents a high-level capability that requires Agent reasoning.
    """
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        prompt_template: str
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.prompt_template = prompt_template
        self.logger = logging.getLogger(f"capability:{name}")

    def format_prompt(self, arguments: Dict[str, Any]) -> str:
        """Format the capability prompt with the given arguments."""
        return self.prompt_template.format(**arguments)

    def to_mcp_tool(self) -> MCPTool:
        """Convert capability to MCP tool representation."""
        return MCPTool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )


class CapabilityRegistry:
    """Registry for agent capabilities that require LLM reasoning."""

    def __init__(self):
        self.capabilities: Dict[str, AgentCapability] = {}
        self.logger = logging.getLogger("capability-registry")

    def register_capability(self, capability: AgentCapability) -> None:
        """Register a capability."""
        self.capabilities[capability.name] = capability
        self.logger.info(f"Registered capability: {capability.name}")

    def get_capability(self, name: str) -> Optional[AgentCapability]:
        """Get a capability by name."""
        return self.capabilities.get(name)

    def list_capabilities(self) -> List[AgentCapability]:
        """List all available capabilities."""
        return list(self.capabilities.values())

    async def load_from_config(self, config: Dict[str, Any]) -> None:
        """
        Load capabilities from configuration.

        Args:
            config: Configuration dictionary
        """
        capabilities_config = config.get("capabilities", [])
        for capability_config in capabilities_config:
            if not isinstance(capability_config, dict):
                continue

            try:
                capability = AgentCapability(
                    name=capability_config["name"],
                    description=capability_config.get("description", ""),
                    input_schema=capability_config.get("input_schema", {}),
                    prompt_template=capability_config.get("prompt_template", "")
                )
                self.register_capability(capability)
            except KeyError as e:
                self.logger.error(f"Error loading capability from config: missing field {e}")
            except Exception as e:
                self.logger.error(f"Error loading capability from config: {e}")
