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

from src.utils.context import get_context, Context


class ServerConnection:
    """
    Represents a connection to an MCP server including its session and lifecycle management.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.session: Optional[ClientSession] = None
        self._init_task: Optional[asyncio.Task] = None
        self._init_complete = asyncio.Event()
        self._cleanup_lock = asyncio.Lock()
        self._is_cleaning_up = False
        self.logger = logging.getLogger(f"mcp-connection:{name}")

    async def initialize(self) -> None:
        """Start the initialization process in a background task."""
        if self._init_task is not None:
            # Already initializing or initialized
            await self._init_complete.wait()
            return

        # Create and start the initialization task
        self._init_task = asyncio.create_task(self._initialize_impl())

        # Wait for initialization to complete
        await self._init_complete.wait()

    async def _initialize_impl(self) -> None:
        """Implementation of the initialization process that runs in its own task."""
        exit_stack = AsyncExitStack()
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
            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport

            # Create and initialize session
            session = await exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            # Store session
            self.session = session

            # Store exit_stack in a task-local attribute
            asyncio.current_task()._exit_stack = exit_stack

            # Register session in global context
            context = get_context()
            context.register_session(self.name, session)

            self.logger.info(f"Server {self.name} initialized successfully")

            # Signal initialization is complete
            self._init_complete.set()

            # Keep the task running until canceled
            try:
                # This keeps the task alive until it's canceled
                await asyncio.Future()
            except asyncio.CancelledError:
                self.logger.info(f"Server {self.name} task canceled, cleaning up resources")
                # Important: The AsyncExitStack is closed in the same task it was created in
                await exit_stack.aclose()
                raise

        except asyncio.CancelledError:
            # Propagate cancellation
            raise
        except Exception as e:
            self.logger.error(f"Error initializing server {self.name}: {e}")
            # Signal initialization is complete (but failed)
            self._init_complete.set()
            raise
        finally:
            # Ensure exit_stack is closed in case of any other exception
            if 'exit_stack' in locals():
                await exit_stack.aclose()

    async def wait_until_initialized(self) -> None:
        """Wait until the server is initialized."""
        await self._init_complete.wait()

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            if self._is_cleaning_up:
                # Already cleaning up
                return

            self._is_cleaning_up = True

            try:
                # Cancel the initialization/server task if it's running
                if self._init_task and not self._init_task.done():
                    self.logger.info(f"Canceling server task for {self.name}")
                    self._init_task.cancel()
                    try:
                        await self._init_task
                    except asyncio.CancelledError:
                        # This is expected
                        pass
                    except Exception as e:
                        self.logger.error(f"Error canceling task for {self.name}: {e}")

                # Remove from context
                context = get_context()
                context.remove_session(self.name)

                self.session = None
                self.logger.info(f"Server {self.name} cleaned up")
            except Exception as e:
                self.logger.error(f"Error during cleanup of server {self.name}: {e}")
            finally:
                self._is_cleaning_up = False


class MCPConnectionManager:
    """
    Manages multiple MCP server connections.
    """

    def __init__(self):
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logging.getLogger("mcp-connection-manager")
        self._cleanup_lock = asyncio.Lock()
        self._is_cleaning_up = False

    async def connect_server(self, name: str, config: Dict[str, Any]) -> ServerConnection:
        """Connect to a server and return the connection."""
        if name in self.connections:
            # If already connecting/connected, return existing connection
            connection = self.connections[name]
            await connection.wait_until_initialized()
            return connection

        # Create new connection
        connection = ServerConnection(name, config)
        self.connections[name] = connection

        # Start initialization process and wait for it to complete
        await connection.initialize()
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
        async with self._cleanup_lock:
            if self._is_cleaning_up:
                # Already cleaning up
                return

            self._is_cleaning_up = True

            try:
                # Create a copy of keys to avoid modifying during iteration
                server_names = list(self.connections.keys())
                for name in server_names:
                    try:
                        await self.disconnect_server(name)
                    except Exception as e:
                        self.logger.error(f"Error disconnecting server {name}: {e}")
            finally:
                self._is_cleaning_up = False

    async def __aenter__(self) -> 'MCPConnectionManager':
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit, disconnects all servers."""
        await self.disconnect_all()
