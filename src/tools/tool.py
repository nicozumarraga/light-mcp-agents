"""
Represents MCP tools with execution capabilities.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from mcp import ClientSession

from src.utils.context import get_context
from src.mcp.mcp_connection_manager import MCPConnectionManager


class Tool:
    """
    Represents a tool with its metadata and execution capabilities.
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name
        self.logger = logging.getLogger(f"tool:{name}")

    # _TODO: Might want to move the formatting to each of the LLM provider classes, to adjust for each provider.
    def format_for_llm(self) -> str:
        """Format tool information for LLM consumption."""
        args_desc = []

        if "properties" in self.input_schema:
            for param_name, param_info in self.input_schema["properties"].items():
                arg_desc = f"- {param_name}: {param_info.get('description', 'No description')}"

                if param_name in self.input_schema.get("required", []):
                    arg_desc += " (required)"

                args_desc.append(arg_desc)

        return f"""
Tool: {self.name}
Description: {self.description}
Arguments:
{chr(10).join(args_desc)}
Server: {self.server_name}
"""

    async def execute(
        self,
        arguments: Dict[str, Any],
        connection_manager: MCPConnectionManager,
        retries: int = 2,
        delay: float = 1.0
    ) -> Any:
        """Execute the tool with retry mechanism."""
        attempt = 0

        while attempt < retries:
            try:
                # Get session for server
                session = await connection_manager.get_session(self.server_name)

                if not session:
                    raise RuntimeError(f"Server {self.server_name} not initialized")

                self.logger.info(f"Executing {self.name} with arguments: {arguments}")

                # Execute tool
                result = await session.call_tool(self.name, arguments)

                self.logger.info(f"Tool {self.name} execution result: {result}")
                return result

            except Exception as e:
                attempt += 1
                self.logger.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}"
                )

                if attempt < retries:
                    self.logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Max retries reached. Failing tool {self.name}")
                    raise


class ToolRegistry:
    """
    Registry for available tools across all servers.
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.logger = logging.getLogger("tool-registry")

    def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name} from server {tool.server_name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all available tools."""
        return list(self.tools.values())

    def clear(self) -> None:
        """Clear all registered tools."""
        self.tools.clear()

    async def load_from_config(
        self,
        config: Dict[str, Any],
        connection_manager: MCPConnectionManager
    ) -> None:
        """
        Load tools from MCP servers defined in configuration.

        Args:
            config: Configuration dictionary
            connection_manager: Connection manager for server access
        """
        # Discover tools from servers
        servers = config.get("servers", {})
        for server_name in servers:
            self.logger.info(f"Discovering tools from server: {server_name}")
            await self.discover_tools(connection_manager, server_name)

    async def discover_tools(
        self,
        connection_manager: MCPConnectionManager,
        server_name: str
    ) -> List[Tool]:
        """
        Discover tools from a server and register them.
        """
        discovered_tools = []

        try:
            session = await connection_manager.get_session(server_name)
            if not session:
                self.logger.error(f"Server {server_name} not initialized")
                return []

            tools_response = await session.list_tools()

            for item in tools_response:
                if isinstance(item, tuple) and item[0] == "tools":
                    for tool_info in item[1]:
                        tool = Tool(
                            name=tool_info.name,
                            description=tool_info.description,
                            input_schema=tool_info.inputSchema,
                            server_name=server_name,
                        )

                        self.register_tool(tool)
                        discovered_tools.append(tool)

            self.logger.info(f"Discovered {len(discovered_tools)} tools from server {server_name}")
            return discovered_tools

        except Exception as e:
            self.logger.error(f"Error discovering tools from server {server_name}: {e}")
            return []
