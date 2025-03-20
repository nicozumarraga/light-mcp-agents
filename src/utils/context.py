"""
A central context object to store global state that is shared across the application.
This lightweight implementation is inspired by the MCP agent example.
"""

from typing import Any, Dict, Optional
import asyncio
import logging
from dataclasses import dataclass, field

from mcp import ClientSession


@dataclass
class Context:
    """
    Context that is passed around through the application.
    This is a global context that is shared across the application.
    """
    config: Dict[str, Any] = field(default_factory=dict)
    sessions: Dict[str, ClientSession] = field(default_factory=dict)

    # Optional handlers and settings
    llm_api_key: Optional[str] = None
    llm_provider: str = "groq"

    def __post_init__(self):
        # Set up logging
        self.logger = logging.getLogger("mcp-agent")

    def get_session(self, server_name: str) -> Optional[ClientSession]:
        """Get a session by server name."""
        return self.sessions.get(server_name)

    def register_session(self, server_name: str, session: ClientSession) -> None:
        """Register a session for a server."""
        self.sessions[server_name] = session

    def remove_session(self, server_name: str) -> None:
        """Remove a session for a server."""
        if server_name in self.sessions:
            del self.sessions[server_name]


# Global context instance
_global_context: Optional[Context] = None


def get_context() -> Context:
    """
    Get the global context instance. Initialize if not exists.
    """
    global _global_context
    if _global_context is None:
        _global_context = Context()
    return _global_context


def set_context(context: Context) -> None:
    """
    Set the global context instance.
    """
    global _global_context
    _global_context = context


async def initialize_context(config: Dict[str, Any]) -> Context:
    """Initialize the context with configuration."""
    context = get_context()
    context.config = config

    # Add any additional initialization logic here

    return context


async def cleanup_context() -> None:
    """Clean up resources in the context."""
    context = get_context()
    logger = logging.getLogger("cleanup-context")

    # Log session names to help with debugging
    if context.sessions:
        session_names = list(context.sessions.keys())
        logger.info(f"Sessions still in context: {session_names}")

    # Just clear the sessions dictionary without trying to clean up individual sessions
    # as they should be cleaned up by the connection manager
    context.sessions.clear()

    # Clear config and reset any other state as needed
    context.config = {}
