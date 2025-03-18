"""
Manages the lifecycle of MCP server connections.
A lightweight implementation for handling connections to MCP servers.
"""

import asyncio
import logging
import os
import shutil
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from context import get_context, Context


class ServerConnection:
    """
    Represents a connection to an MCP server including its session and lifecycle management.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._initialized = asyncio.Event()
        self._cleanup_lock = asyncio.Lock()
        self.logger = logging.getLogger(f"mcp-connection:{name}")

    async def initialize(self) -> ClientSession:
        """Initialize the server connection and return the session."""
        try:
            # Get the command to run
            command = (
                shutil.which("npx")
                if self.config["command"] == "npx"
                else self.config["command"]
            )
            if command is None:
                raise ValueError(f"Invalid command for server {self.name}")

            # Set up environment variables
            env = os.environ.copy()
            if self.config.get("env"):
                env.update(self.config["env"])

            # Create server parameters
            server_params = StdioServerParameters(
                command=command,
                args=self.config["args"],
                env=env,
            )

            # Initialize stdio client
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport

            # Create and initialize session
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            # Store session and mark as initialized
            self.session = session
            self._initialized.set()

            # Register session in global context
            context = get_context()
            context.register_session(self.name, session)

            self.logger.info(f"Server {self.name} initialized successfully")
            return session

        except Exception as e:
            self.logger.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def wait_until_initialized(self) -> None:
        """Wait until the server is initialized."""
        await self._initialized.wait()

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()

                # Remove from context
                context = get_context()
                context.remove_session(self.name)

                self.session = None
                self.logger.info(f"Server {self.name} cleaned up")
            except Exception as e:
                self.logger.error(f"Error during cleanup of server {self.name}: {e}")


class MCPConnectionManager:
    """
    Manages multiple MCP server connections.
    """

    def __init__(self):
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logging.getLogger("mcp-connection-manager")

    async def connect_server(self, name: str, config: Dict[str, Any]) -> ServerConnection:
        """Connect to a server and return the connection."""
        if name in self.connections:
            # If already connecting/connected, return existing connection
            return self.connections[name]

        # Create new connection
        connection = ServerConnection(name, config)
        self.connections[name] = connection

        # Initialize in background
        asyncio.create_task(connection.initialize())

        return connection

    async def get_session(self, name: str) -> Optional[ClientSession]:
        """Get the session for a server."""
        if name not in self.connections:
            return None

        connection = self.connections[name]
        await connection.wait_until_initialized()
        return connection.session

    async def disconnect_server(self, name: str) -> None:
        """Disconnect from a server."""
        if name in self.connections:
            connection = self.connections[name]
            await connection.cleanup()
            del self.connections[name]

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for name in list(self.connections.keys()):
            await self.disconnect_server(name)

    async def __aenter__(self) -> 'MCPConnectionManager':
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit, disconnects all servers."""
        await self.disconnect_all()
