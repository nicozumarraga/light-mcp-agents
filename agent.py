"""
Agent class for orchestrating interactions between LLM and tools.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Type

from base_llm import BaseLLM
from context import get_context
from mcp_connection_manager import MCPConnectionManager
from tool import Tool, ToolRegistry


class Agent:
    """
    An agent that orchestrates interactions between an LLM and MCP tools.
    """

    def __init__(
        self,
        llm_client: BaseLLM,
        connection_manager: MCPConnectionManager,
        tool_registry: ToolRegistry,
        max_tool_chain_length: int = 10,
        name: str = "agent"
    ):
        self.llm_client = llm_client
        self.connection_manager = connection_manager
        self.tool_registry = tool_registry
        self.max_tool_chain_length = max_tool_chain_length
        self.name = name
        self.logger = logging.getLogger(f"agent:{name}")

    async def process_llm_response(self, llm_response: str) -> Tuple[str, bool, str]:
        """Process the LLM response, separate text from tool calls.

        Args:
            llm_response: Response from the LLM

        Returns:
            Tuple of (processed_result, is_tool_call, human_readable_text)
        """
        # Regular expression to find JSON objects
        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_pattern, llm_response)

        # Start with the full text as human readable
        human_readable_text = llm_response

        # Try each potential JSON match
        for match in matches:
            try:
                tool_call = json.loads(match)

                # Check if it's a valid tool call
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

    async def execute_tool_call(self, tool_call: Dict[str, Any]) -> Tuple[str, bool]:
        """Execute a tool call.

        Args:
            tool_call: The parsed tool call dictionary

        Returns:
            Tuple of (tool_result, is_tool_call)
        """
        self.logger.info(f"Executing tool: {tool_call['tool']}")
        self.logger.info(f"With arguments: {tool_call['arguments']}")

        tool = self.tool_registry.get_tool(tool_call["tool"])

        if tool:
            try:
                result = await tool.execute(
                    arguments=tool_call["arguments"],
                    connection_manager=self.connection_manager,
                )

                if isinstance(result, dict) and "progress" in result:
                    progress = result["progress"]
                    total = result["total"]
                    percentage = (progress / total) * 100
                    self.logger.info(f"Progress: {progress}/{total} ({percentage:.1f}%)")

                return f"Tool execution result: {result}", True
            except Exception as e:
                error_msg = f"Error executing tool: {str(e)}"
                self.logger.error(error_msg)
                return error_msg, False

        return f"No tool found with name: {tool_call['tool']}", False

    def create_tools_system_message(self) -> str:
        """Create the system message with tool descriptions."""
        tools = self.tool_registry.list_tools()
        tools_description = "\n".join([tool.format_for_llm() for tool in tools])

        return (
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

    async def start_conversation(self) -> None:
        """Start a conversation with the user."""
        try:
            # Create system message with available tools
            system_message = self.create_tools_system_message()
            messages = [{"role": "system", "content": system_message}]

            while True:
                try:
                    user_input = input("You: ").strip()
                    if user_input.lower() in ["quit", "exit"]:
                        self.logger.info("Exiting conversation...")
                        break

                    # Add user message
                    messages.append({"role": "user", "content": user_input})

                    # Chain of thought loop
                    chain_length = 0
                    is_tool_call = True
                    final_response_shown = False

                    while is_tool_call and chain_length < self.max_tool_chain_length:
                        # Get response from LLM
                        llm_response = self.llm_client.get_response(messages)

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
                        self.logger.warning(warning)
                        messages.append({"role": "system", "content": warning})

                        # Get final response
                        final_response = self.llm_client.get_response(messages)
                        self.logger.info(f"Final response after limit: {final_response}")
                        messages.append({"role": "assistant", "content": final_response})
                        print(f"Assistant: {final_response}")

                except KeyboardInterrupt:
                    print("\nConversation interrupted. Exiting...")
                    break

        finally:
            # We no longer clean up connection manager here - that's done in main.py
            self.logger.info("Conversation ended")
