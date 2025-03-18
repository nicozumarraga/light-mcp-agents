import asyncio
import logging
from typing import Dict, Any

from agent import Agent
from base_llm import BaseLLM
from config import load_config
from context import get_context, initialize_context, cleanup_context
from groq_llm import GroqLLM
from mcp_connection_manager import MCPConnectionManager
from tool import ToolRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")


def create_llm_client(api_key: str, provider: str) -> BaseLLM:
    """Create an LLM client based on the configured provider."""
    if provider == "groq":
        return GroqLLM(api_key)
    # Add other providers as needed
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


async def main() -> None:
    """Initialize and run the agent."""
    try:
        # Load configuration
        config = load_config("servers_config.json")

        # Initialize context
        context = await initialize_context(config.to_dict())

        # Create LLM client
        llm_client = create_llm_client(config.llm_api_key, config.llm_provider)

        # Initialize connection manager
        connection_manager = MCPConnectionManager()

        # Initialize tool registry
        tool_registry = ToolRegistry()

        # Connect to each server and discover tools
        for name, server_config in config.server_configs.items():
            logger.info(f"Connecting to server: {name}")
            await connection_manager.connect_server(
                name, server_config.to_dict()
            )

            # Discover tools from this server
            logger.info(f"Discovering tools from server: {name}")
            await tool_registry.discover_tools(connection_manager, name)

        # Create and start the agent
        agent = Agent(
            llm_client=llm_client,
            connection_manager=connection_manager,
            tool_registry=tool_registry,
        )

        logger.info("Starting agent conversation...")
        await agent.start_conversation()

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        # Clean up all resources
        logger.info("Cleaning up resources...")
        await cleanup_context()


if __name__ == "__main__":
    asyncio.run(main())
