import asyncio
import json
import logging
import os
import shutil
from contextlib import AsyncExitStack
from typing import Any, List, Dict, Optional, Type

import httpx
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from base_llm import BaseLLM
from groq_llm import GroqLLM

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Configuration:
    """Manages configuration and environment variables for the MCP client."""

    def __init__(self) -> None:
        """Initialize configuration with environment variables."""
        self.load_env()
        self.api_key = os.getenv("LLM_API_KEY")
        self.llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()

    @staticmethod
    def load_env() -> None:
        """Load environment variables from .env file."""
        load_dotenv()

    @staticmethod
    def load_config(file_path: str) -> dict[str, Any]:
        """Load server configuration from JSON file.

        Args:
            file_path: Path to the JSON configuration file.

        Returns:
            Dict containing server configuration.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            JSONDecodeError: If configuration file is invalid JSON.
        """
        with open(file_path, "r") as f:
            return json.load(f)

    @property
    def llm_api_key(self) -> str:
        """Get the LLM API key.

        Returns:
            The API key as a string.

        Raises:
            ValueError: If the API key is not found in environment variables.
        """
        if not self.api_key:
            raise ValueError("LLM_API_KEY not found in environment variables")
        return self.api_key

    def create_llm_client(self) -> BaseLLM:
        """Create an LLM client based on the configured provider.

        Returns:
            An instance of a BaseLLM subclass.

        Raises:
            ValueError: If the LLM provider is not supported.
        """
        if self.llm_provider == "groq":
            return GroqLLM(self.llm_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")


class Server:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.stdio_context: Any | None = None
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = (
            shutil.which("npx")
            if self.config["command"] == "npx"
            else self.config["command"]
        )
        if command is None:
            raise ValueError("The command must be a valid string and cannot be None.")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env={**os.environ, **self.config["env"]}
            if self.config.get("env")
            else None,
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> list[Any]:
        """List available tools from the server.

        Returns:
            A list of available tools.

        Raises:
            RuntimeError: If the server is not initialized.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools_response = await self.session.list_tools()
        tools = []

        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                for tool in item[1]:
                    tools.append(Tool(tool.name, tool.description, tool.inputSchema))

        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            retries: Number of retry attempts.
            delay: Delay between retries in seconds.

        Returns:
            Tool execution result.

        Raises:
            RuntimeError: If server is not initialized.
            Exception: If tool execution fails after all retries.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        while attempt < retries:
            try:
                logging.info(f"Executing {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)

                return result

            except Exception as e:
                attempt += 1
                logging.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}."
                )
                if attempt < retries:
                    logging.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("Max retries reached. Failing.")
                    raise

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                self.stdio_context = None
            except Exception as e:
                logging.error(f"Error during cleanup of server {self.name}: {e}")


class Tool:
    """Represents a tool with its properties and formatting."""

    def __init__(
        self, name: str, description: str, input_schema: dict[str, Any]
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.input_schema: dict[str, Any] = input_schema

    def format_for_llm(self) -> str:
        """Format tool information for LLM.

        Returns:
            A formatted string describing the tool.
        """
        args_desc = []
        if "properties" in self.input_schema:
            for param_name, param_info in self.input_schema["properties"].items():
                arg_desc = (
                    f"- {param_name}: {param_info.get('description', 'No description')}"
                )
                if param_name in self.input_schema.get("required", []):
                    arg_desc += " (required)"
                args_desc.append(arg_desc)

        return f"""
Tool: {self.name}
Description: {self.description}
Arguments:
{chr(10).join(args_desc)}
"""


class ChatSession:
    """Orchestrates the interaction between user, LLM, and tools."""

    def __init__(self, servers: list[Server], llm_client: BaseLLM) -> None:
        self.servers: list[Server] = servers
        self.llm_client: BaseLLM = llm_client
        self.max_tool_chain_length = 10  # Safety limit to prevent infinite loops

    async def cleanup_servers(self) -> None:
        """Clean up all servers properly."""
        for server in self.servers:
            try:
                # Use a simple direct call to cleanup rather than creating tasks
                await server.cleanup()
            except Exception as e:
                logging.warning(f"Warning during cleanup of server {server.name}: {e}")

    async def process_llm_response(self, llm_response: str) -> tuple[str, bool, str]:
        """Process the LLM response, separate text from tool calls.

        Args:
            llm_response: The response from the LLM.

        Returns:
            Tuple containing (processed_result, is_tool_call, human_readable_text)
        """
        import json
        import re

        # Extract any JSON objects from the text
        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_pattern, llm_response)

        # The human-readable part is what remains if we remove all JSON objects
        human_readable_text = llm_response

        # Try each potential JSON match
        for match in matches:
            try:
                tool_call = json.loads(match)
                if "tool" in tool_call and "arguments" in tool_call:
                    # Remove the JSON from the human-readable text
                    human_readable_text = human_readable_text.replace(match, "").strip()

                    # Execute the tool
                    result, is_tool_call = await self.execute_tool_call(tool_call)
                    return result, is_tool_call, human_readable_text
            except json.JSONDecodeError:
                continue

        # If we get here, no valid tool call was found
        return llm_response, False, human_readable_text

    async def execute_tool_call(self, tool_call: dict) -> tuple[str, bool]:
        """Execute a tool call.

        Args:
            tool_call: The parsed tool call dict.

        Returns:
            Tuple containing (tool_result, is_tool_call)
        """
        logging.info(f"Executing tool: {tool_call['tool']}")
        logging.info(f"With arguments: {tool_call['arguments']}")

        for server in self.servers:
            tools = await server.list_tools()
            if any(tool.name == tool_call["tool"] for tool in tools):
                try:
                    result = await server.execute_tool(
                        tool_call["tool"], tool_call["arguments"]
                    )

                    if isinstance(result, dict) and "progress" in result:
                        progress = result["progress"]
                        total = result["total"]
                        percentage = (progress / total) * 100
                        logging.info(
                            f"Progress: {progress}/{total} ({percentage:.1f}%)"
                        )

                    return f"Tool execution result: {result}", True
                except Exception as e:
                    error_msg = f"Error executing tool: {str(e)}"
                    logging.error(error_msg)
                    return error_msg, False

        return f"No server found with tool: {tool_call['tool']}", False

    async def start(self) -> None:
        """Main chat session handler with progressive responses."""
        try:
            for server in self.servers:
                try:
                    await server.initialize()
                except Exception as e:
                    logging.error(f"Failed to initialize server: {e}")
                    await self.cleanup_servers()
                    return

            all_tools = []
            for server in self.servers:
                tools = await server.list_tools()
                all_tools.extend(tools)

            tools_description = "\n".join([tool.format_for_llm() for tool in all_tools])

            system_message = (
                "You are a helpful assistant with access to these tools:\n\n"
                f"{tools_description}\n"
                "Choose the appropriate tool based on the user's question. "
                "If no tool is needed, reply directly.\n\n"
                "IMPORTANT: When you need to use a tool:\n"
                "1. You can first provide a natural language response to the user\n"
                "2. Then include a tool call in JSON format like this:\n"
                "{\n"
                '    "tool": "tool-name",\n'
                '    "arguments": {\n'
                '        "argument-name": "value"\n'
                "    }\n"
                "}\n\n"
                "When you receive a tool result, you can provide another natural language response "
                "and then decide if you need more information. "
                "If yes, include another tool call in the same format. "
                "If no, simply give your final answer.\n\n"
                "Guidelines for responses:\n"
                "1. Transform raw data into natural, conversational responses\n"
                "2. Keep responses concise but informative\n"
                "3. Focus on the most relevant information\n"
                "4. Maintain a conversational flow\n"
                "Please use only the tools that are explicitly defined above."
            )

            messages = [{"role": "system", "content": system_message}]

            while True:
                try:
                    user_input = input("You: ").strip()
                    if user_input.lower() in ["quit", "exit"]:
                        logging.info("\nExiting...")
                        break

                    messages.append({"role": "user", "content": user_input})

                    # Start chain of thought loop
                    chain_length = 0
                    is_tool_call = True
                    final_response_shown = False

                    while is_tool_call and chain_length < self.max_tool_chain_length:
                        # Get response from LLM
                        llm_response = self.llm_client.get_response(messages)
                        #logging.info(f"\nAssistant (step {chain_length+1}): {llm_response}")

                        # Process response to check for tool calls and extract human-readable text
                        result, is_tool_call, human_text = await self.process_llm_response(llm_response)

                        # Print the human-readable part immediately to the user if it exists
                        if human_text.strip():
                            print(f"Assistant: {human_text}")
                            final_response_shown = True

                        # Add the LLM's response to the conversation
                        messages.append({"role": "assistant", "content": llm_response})

                        # If tool was called, add result and continue chain
                        if is_tool_call:
                            messages.append({"role": "system", "content": result})
                            chain_length += 1
                        elif not final_response_shown:
                            # If no human text was extracted but it's not a tool call, show the full response
                            print(f"Assistant: {llm_response}")
                            final_response_shown = True

                    # If we hit the safety limit
                    if chain_length >= self.max_tool_chain_length:
                        warning = "Maximum chain of thought length reached. Providing final response."
                        logging.warning(warning)
                        messages.append({"role": "system", "content": warning})

                        # Get final response
                        final_response = self.llm_client.get_response(messages)
                        logging.info(f"\nFinal response after limit: {final_response}")
                        messages.append({"role": "assistant", "content": final_response})
                        print(f"Assistant: {final_response}")

                except KeyboardInterrupt:
                    logging.info("\nExiting...")
                    break

        finally:
            await self.cleanup_servers()


async def main() -> None:
    """Initialize and run the chat session."""
    config = Configuration()
    server_config = config.load_config("servers_config.json")
    servers = [
        Server(name, srv_config)
        for name, srv_config in server_config["mcpServers"].items()
    ]
    llm_client = config.create_llm_client()
    chat_session = ChatSession(servers, llm_client)
    await chat_session.start()


if __name__ == "__main__":
    asyncio.run(main())
