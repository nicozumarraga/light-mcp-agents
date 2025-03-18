"""
Factory for creating and initializing the ToolRegistry.
"""

import logging
from typing import List, Optional

from mcp_connection_manager import MCPConnectionManager
from tool import Tool, ToolRegistry


async def discover_tools_for_server(
    tool_registry: ToolRegistry,
    connection_manager: MCPConnectionManager,
    server_name: str
) -> List[Tool]:
    """
    Discover tools from a specific server and register them.

    Args:
        tool_registry: The tool registry to register tools with
        connection_manager: The connection manager to use
        server_name: The name of the server to discover tools from

    Returns:
        List of discovered tools
    """
    logger = logging.getLogger("tool-registry")
    logger.info(f"Discovering tools from server {server_name}")

    try:
        return await tool_registry.discover_tools(connection_manager, server_name)
    except Exception as e:
        logger.error(f"Error discovering tools from server {server_name}: {e}")
        return []


def create_tool_registry() -> ToolRegistry:
    """
    Create and return a new ToolRegistry instance.

    Returns:
        A new ToolRegistry instance
    """
    return ToolRegistry()


async def discover_all_tools(
    tool_registry: ToolRegistry,
    connection_manager: MCPConnectionManager
) -> int:
    """
    Discover tools from all connected servers.

    Args:
        tool_registry: The tool registry to register tools with
        connection_manager: The connection manager to use

    Returns:
        Total number of discovered tools
    """
    logger = logging.getLogger("tool-registry")

    total_tools = 0

    # Get all server names from the connection manager
    server_names = list(connection_manager.connections.keys())

    # Discover tools from each server
    for server_name in server_names:
        tools = await discover_tools_for_server(
            tool_registry, connection_manager, server_name
        )
        total_tools += len(tools)

    logger.info(f"Discovered a total of {total_tools} tools from all servers")
    return total_tools
