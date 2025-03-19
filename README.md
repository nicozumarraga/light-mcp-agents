# Recursive MCP Agent Architecture

This project implements a recursive agent architecture that allows agents to function both as MCP clients and servers. This creates a hierarchical composition model where agents can leverage the capabilities of other agents.

## Key Components

1. **AgentServer**: Main class that manages an agent in both client and server modes
2. **MCPServerWrapper**: Wraps an Agent as an MCP server to expose its tools
3. **Agent**: Core agent implementation that processes user requests and executes tools
4. **AgentTool**: Registry for local tool implementations that can be used directly by agents
5. **ToolRegistry**: Registry for all tools (both local and from remote servers)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration Files

### Basic Agent

Create a configuration file for your agent (e.g., `my_agent_config.json`):

```json
{
  "agent_name": "my-agent",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "server_mode": false,
  "servers": {
    "tool-server": {
      "command": "npx",
      "args": ["@anthropic-ai/mcp-tooling", "start", "-q"],
      "env": {
        "PORT": "3001"
      }
    }
  }
}
```

### Agent with Local Tools

You can also define tools directly in the configuration:

```json
{
  "agent_name": "my-agent",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "tools": [
    {
      "name": "custom_tool",
      "description": "A custom tool",
      "server_name": "local",
      "input_schema": {
        "type": "object",
        "properties": {
          "param1": {
            "type": "string",
            "description": "Parameter 1"
          }
        },
        "required": ["param1"]
      }
    }
  ]
}
```

### Orchestrator Agent

For an orchestrator agent that connects to other agents:

```json
{
  "agent_name": "orchestrator",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "servers": {
    "agent1": {
      "command": "python",
      "args": ["agent_runner.py", "--config=agent1_config.json", "--server-mode"],
      "env": {}
    },
    "agent2": {
      "command": "python",
      "args": ["agent_runner.py", "--config=agent2_config.json", "--server-mode"],
      "env": {}
    }
  }
}
```

## Running an Agent

### Client Mode (Interactive)

```bash
python agent_runner.py --config=my_agent_config.json
```

### Server Mode

```bash
python agent_runner.py --config=my_agent_config.json --server-mode
```

You can also specify a custom server name:

```bash
python agent_runner.py --config=my_agent_config.json --server-mode --server-name=my-custom-server
```

## Creating Local Tools

Create a Python file with tool implementations using the `@agent_tools.register` decorator:

```python
from agent_tool import agent_tools

@agent_tools.register
async def my_tool(param1: str, param2: int = 0) -> str:
    """Tool description goes here."""
    return f"Processed {param1} with {param2}"

@agent_tools.register(name="custom_name", description="Custom description")
async def another_tool(input_data: str) -> str:
    return f"Processed: {input_data}"
```

Import this file in your application to register the tools with the agent.

## Creating a Hierarchical Agent Structure

1. Create configuration files for base agents
2. Set them to run in server mode
3. Create an orchestrator configuration that connects to the base agents
4. Run the orchestrator to interact with all agent capabilities

## Example Workflow

1. Start base agents in server mode:
   ```bash
   python agent_runner.py --config=agent1_config.json --server-mode
   python agent_runner.py --config=agent2_config.json --server-mode
   ```

2. Start the orchestrator agent in client mode:
   ```bash
   python agent_runner.py --config=orchestrator_config.json
   ```

The orchestrator will connect to both base agents and can use all their tools as if they were its own.

## Architecture Benefits

1. **Hierarchical Composition**: Agents can use other agents' capabilities
2. **Encapsulation**: Each agent encapsulates a specific domain or capability
3. **Scalability**: Easy to add new agents to the hierarchy
4. **Flexibility**: Agents can run in client mode, server mode, or both
5. **Reusability**: Agent capabilities can be reused across different contexts
