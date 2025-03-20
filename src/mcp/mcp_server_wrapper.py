"""
MCPServerWrapper class for exposing an Agent as an MCP server.
"""

import logging
from typing import Dict, Any, List, Optional

from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Tool as MCPTool, TextContent

from src.agent.agent import Agent
from src.tools.tool import Tool


class MCPServerWrapper(Server):
    """
    Wraps an Agent as an MCP server, exposing its tools to other clients.
    """

    def __init__(self, agent: Agent, name: str = None):
        super().__init__(name or f"agent-server-{id(agent)}")
        self.agent = agent
        self.logger = logging.getLogger(f"mcp-server-wrapper:{name}")

        # Register MCP server handlers
        self.list_tools()(self._list_tools)
        self.call_tool()(self._call_tool)

    async def _list_tools(self) -> List[MCPTool]:
        """List all tools and capabilities from the agent."""
        self.logger.info("Listing tools and capabilities from agent's registries")

        # Get regular tools
        tools = self.agent.tool_registry.list_tools()
        tool_schemas = [self._convert_to_mcp_tool(tool) for tool in tools]

        # Get capabilities as tools
        capabilities = self.agent.capability_registry.list_capabilities()
        capability_schemas = [capability.to_mcp_tool() for capability in capabilities]

        # Combine and return all tools
        return tool_schemas + capability_schemas

    async def _call_tool(self, name: str, arguments: dict = None) -> List[TextContent]:
        """Execute a tool or capability through the agent."""
        arguments = arguments or {}
        self.logger.info(f"Calling tool/capability: {name} with arguments: {arguments}")

        try:
            # Check if it's a capability
            capability = self.agent.capability_registry.get_capability(name)
            if capability:
                # Execute as a capability with LLM reasoning
                self.logger.info(f"Executing as capability: {name}")
                result = await self.agent.execute_capability(name, arguments)
                return [TextContent(type="text", text=result)]

            # Otherwise, handle as a regular tool
            tool_call = {"tool": name, "arguments": arguments}
            result, is_tool_call = await self.agent.execute_tool_call(tool_call)

            self.logger.info(f"Tool/capability execution result: {result}")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            error_msg = f"Error executing tool/capability {name}: {str(e)}"
            self.logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    def _convert_to_mcp_tool(self, tool: Tool) -> MCPTool:
        """Convert our Tool object to an MCP Tool representation."""
        return MCPTool(
            name=tool.name,
            description=tool.description,
            inputSchema=tool.input_schema
        )

    async def run_stdio_async(self) -> None:
        """Run the server using stdio transport."""
        self.logger.info(f"Starting MCP server for agent")
        async with stdio_server() as (read_stream, write_stream):
            await self.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=self.create_initialization_options()
            )
