# Recursive MCP Agent Architecture

This project implements a recursive agent architecture that allows agents to function both as MCP clients and servers. This creates a hierarchical composition model where agents can leverage the capabilities of other agents.

## Key Components

1. **AgentServer**: Main class that manages an agent in both client and server modes
2. **MCPServerWrapper**: Wraps an Agent as an MCP server to expose its tools
3. **Agent**: Core agent implementation that processes user requests and executes tools
4. **CapabilityRegistry**: Registry for agent capabilities that require LLM reasoning
5. **ToolRegistry**: Registry for all tools from MCP servers

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

### Agent with Capabilities

You can define advanced capabilities that require LLM reasoning:

```json
{
  "agent_name": "research-agent",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "capabilities": [
    {
      "name": "summarize_document",
      "description": "Summarize a document in a concise way",
      "input_schema": {
        "type": "object",
        "properties": {
          "document_text": {
            "type": "string",
            "description": "The text of the document to summarize"
          },
          "max_length": {
            "type": "integer",
            "description": "Maximum length of the summary in words",
            "default": 200
          }
        },
        "required": ["document_text"]
      },
      "prompt_template": "Summarize the following document in {max_length} words or fewer:\n\n{document_text}"
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

## Agent Capabilities

Agent capabilities are high-level functions that require LLM reasoning, defined in your configuration file:

1. **Defining Capabilities**: Each capability has a name, description, input schema, and prompt template
2. **Prompt Templates**: Use string formatting syntax (e.g., `{parameter_name}`) to insert arguments
3. **Execution Flow**: When a capability is called, the agent will:
   - Format the prompt with the provided arguments
   - Start a reasoning process with access to its tools
   - Return the final result after the reasoning is complete

Capabilities are automatically exposed as tools to higher-level agents, allowing for complex delegation.

## Example Workflow with Capabilities

1. Start a specialized agent with capabilities in server mode:
   ```bash
   python agent_runner.py --config=research_agent_config.json --server-mode
   ```

2. Start the orchestrator that connects to this agent:
   ```bash
   python agent_runner.py --config=master_orchestrator_config.json
   ```

3. The orchestrator can now delegate complex tasks to the specialized agent using its capabilities:
   ```
   You: Can you help me research machine learning?
   ```

4. The orchestrator will delegate to the research agent's "research_topic" capability, which will:
   - Start its own reasoning process about machine learning
   - Use its search tools to gather information
   - Return a comprehensive response to the orchestrator
   - The orchestrator will then present the results to you

## Architecture Benefits

1. **Hierarchical Composition**: Agents can use other agents' capabilities
2. **Encapsulation**: Each agent encapsulates a specific domain or capability
3. **Reasoning Delegation**: Complex tasks can be delegated to specialized agents
4. **Flexibility**: Capabilities can use any tools available to the agent
5. **Configuration-Driven**: Define capabilities through simple configuration files
