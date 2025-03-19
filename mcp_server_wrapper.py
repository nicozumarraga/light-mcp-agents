"""
MCPServerWrapper class for exposing an Agent as an MCP server.
"""

import logging
from typing import Dict, Any, List, Optional

from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Tool as MCPTool, TextContent

from agent import Agent
from tool import Tool


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
        """List all tools from the agent's tool registry."""
        self.logger.info("Listing tools from agent's tool registry")
        tools = self.agent.tool_registry.list_tools()
        return [self._convert_to_mcp_tool(tool) for tool in tools]

    async def _call_tool(self, name: str, arguments: dict = None) -> List[TextContent]:
        """Execute a tool through the agent."""
        self.logger.info(f"Calling tool: {name} with arguments: {arguments}")
        try:
            # Format the tool call as expected by the agent
            tool_call = {"tool": name, "arguments": arguments or {}}

            # Execute the tool call through the agent
            result, is_tool_call = await self.agent.execute_tool_call(tool_call)

            self.logger.info(f"Tool execution result: {result}")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            error_msg = f"Error executing tool {name}: {str(e)}"
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
