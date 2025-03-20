"""
AgentServer class for managing an agent in both client and server modes.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional

from src.agent.agent import Agent
from src.llm.base_llm import BaseLLM
from src.llm.groq_llm import GroqLLM
from src.utils.context import get_context, initialize_context, cleanup_context
from src.mcp.mcp_connection_manager import MCPConnectionManager
from src.tools.tool import ToolRegistry
from src.capabilities.capability import CapabilityRegistry
from src.mcp.mcp_server_wrapper import MCPServerWrapper


class AgentServer:
    """
    Manages an agent that can operate both as a client and as a server.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        server_mode: bool = False,
        server_name: str = None
    ):
        self.config = config
        self.server_mode = server_mode
        self.server_name = server_name or config.get("server_name", f"agent-server-{id(self)}")
        self.agent = None
        self.server = None
        self.connection_manager = None
        self.tool_registry = None
        self.capability_registry = None
        self.llm_client = None
        self.logger = logging.getLogger("agent-server")

    async def initialize(self):
        """Initialize the agent and server if in server mode."""
        # Initialize context
        await initialize_context(self.config)
        context = get_context()

        # Create connection manager
        self.connection_manager = MCPConnectionManager()

        # Create registries
        self.tool_registry = ToolRegistry()
        self.capability_registry = CapabilityRegistry()

        # Create LLM client
        self.llm_client = self._create_llm_client()

        # Create agent
        self.agent = Agent(
            llm_client=self.llm_client,
            connection_manager=self.connection_manager,
            tool_registry=self.tool_registry,
            capability_registry=self.capability_registry,
            name=self.config.get("agent_name", "agent")
        )

        # Connect to servers and discover tools
        await self._connect_to_servers_and_discover_tools()

        # Load capabilities from config
        await self._load_capabilities()

        # If in server mode, initialize the server wrapper
        if self.server_mode:
            self.server = MCPServerWrapper(self.agent, self.server_name)
            self.logger.info(f"Initialized agent in server mode with name: {self.server_name}")
        else:
            self.logger.info(f"Initialized agent in client-only mode")

        return self

    async def run(self):
        """Run the agent in the appropriate mode."""
        if self.server_mode:
            # Run as a server
            self.logger.info(f"Running agent as server with name: {self.server_name}")
            await self.server.run_stdio_async()
        else:
            # Run as a standalone agent
            self.logger.info("Running agent in interactive conversation mode")
            await self.agent.start_conversation()

    async def cleanup(self):
        """Clean up agent resources."""
        try:
            self.logger.info("Cleaning up agent resources")
            if self.connection_manager:
                await self.connection_manager.disconnect_all()
            await cleanup_context()
            self.logger.info("Cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def _connect_to_servers_and_discover_tools(self):
        """Connect to servers and discover their tools."""
        try:
            # First establish connections to all servers
            servers = self.config.get("servers", {})
            for name, server_config in servers.items():
                self.logger.info(f"Connecting to server: {name}")
                await self.connection_manager.connect_server(name, server_config)

            # Then discover tools from all servers
            self.logger.info("Discovering tools from servers")
            await self.tool_registry.load_from_config(self.config, self.connection_manager)

            # Log the tools that were discovered
            tools = self.tool_registry.list_tools()
            self.logger.info(f"Discovered {len(tools)} tools from MCP servers")
        except Exception as e:
            self.logger.error(f"Error connecting to servers or discovering tools: {e}")
            raise

    async def _load_capabilities(self):
        """Load capabilities from the configuration."""
        try:
            self.logger.info("Loading capabilities from configuration")
            await self.capability_registry.load_from_config(self.config)

            # Log the capabilities that were loaded
            capabilities = self.capability_registry.list_capabilities()
            self.logger.info(f"Loaded {len(capabilities)} capabilities from configuration")
        except Exception as e:
            self.logger.error(f"Error loading capabilities: {e}")
            raise

    def _create_llm_client(self) -> BaseLLM:
        """Create an LLM client based on configuration."""
        provider = self.config.get("llm_provider", "groq")
        api_key = self.config.get("llm_api_key", "")

        self.logger.info(f"Creating LLM client with provider: {provider}")

        if provider == "groq":
            return GroqLLM(api_key)
        # TODO: add more providers (Anthropic, OpenAI...)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
