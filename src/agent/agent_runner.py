#!/usr/bin/env python
"""
Runner script for starting an agent in client or server mode.
"""

import asyncio
import argparse
import json
import logging
import sys
import os
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent.agent_server import AgentServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("agent-runner")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        sys.exit(1)


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run an MCP agent in client or server mode")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument("--server-mode", action="store_true", help="Run in server mode")
    parser.add_argument("--server-name", help="Server name to use in server mode")
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Determine server mode from args or config
    server_mode = args.server_mode or config.get("server_mode", False)
    server_name = args.server_name or config.get("server_name")

    # Create and initialize agent server
    agent_server = None
    try:
        logger.info(f"Starting agent {'in server mode' if server_mode else 'in client mode'}")

        agent_server = AgentServer(
            config=config,
            server_mode=server_mode,
            server_name=server_name
        )

        await agent_server.initialize()
        await agent_server.run()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error running agent: {e}", exc_info=True)
        return 1
    finally:
        if agent_server:
            logger.info("Cleaning up resources...")
            await agent_server.cleanup()

    return 0


if __name__ == "__main__":
    asyncio.run(main())
