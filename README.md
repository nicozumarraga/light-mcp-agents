# 🚀 Light MCP Agents 

## What is it?

Light MCP Agents is a lightweight framework for building and orchestrating AI agents using the Model Context Protocol (MCP). It enables the creation of hierarchical agent systems where specialized agents can delegate tasks, share capabilities, and collaborate to solve complex problems.
With a configuration-driven approach, you can quickly build sophisticated agent networks without extensive coding in a composable architecture.

## Why does it matter?

✅ Create agents connecting to any MCP Server with a simple configuration file.
✅ Create multi-agent workflows with no additional code. Just one config file per agent.
✅ Easily share your agents configurations with others to run.

## Architecture Overview
<img width="725" alt="light-mcp-agents-diagram" src="https://github.com/user-attachments/assets/9a69e2da-403e-40e3-9f6f-4cf484dc7444" />

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/nicozumarraga/light-mcp-agents.git
cd light-mcp-agents

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Your First Agent

```bash
# Run the base agent example (simple client agent)
python src/agent/agent_runner.py --config examples/base_agent/base_agent_config.json
```

If successful, you'll be able to chat with the agent and use its tools!

### Try a Multi-Agent Example

In one terminal, start the research agent in server mode:
```bash
python src/agent/agent_runner.py --config examples/orchestrator_researcher/research_agent_config.json --server-mode
```

In a second terminal, start the orchestrator that connects to the research agent:
```bash
python src/agent/agent_runner.py --config examples/orchestrator_researcher/master_orchestrator_config.json
```

Now you can ask the orchestrator to research topics for you, and it will delegate to the specialized research agent or use its tools directly.

## Example Agents

The repository includes example agents in the `examples/` directory:

1. **Base Agent** (`examples/base_agent/`)
   - A simple agent that connects to external tool servers
   - Good first example to understand how agents work

2. **Orchestrator-Researcher** (`examples/orchestrator_researcher/`)
   - Demonstrates a hierarchical agent structure
   - Shows how capabilities can be shared between agents

## Running Options

### Basic Command Structure

```bash
python src/agent/agent_runner.py --config <config_file_path>
```

### Additional Options

```bash
# Run in server mode (makes it available to other agents)
python src/agent/agent_runner.py --config <config_file_path> --server-mode

# Run with a custom server name
python src/agent/agent_runner.py --config <config_file_path> --server-mode --server-name "my-custom-server"
```

### Troubleshooting

If you encounter issues running the examples:

1. Check that your LLM API keys are properly configured in the config files
2. Make sure any external tool servers (like search tools) are accessible
3. Verify that Python can find the modules (the src directory should be in your Python path)
4. Check the logs for any specific error messages

## Creating Your Own Agents

### Basic Agent Configuration

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

To create an agent with special capabilities:

```json
{
  "agent_name": "research-agent",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "server_mode": true,
  "server_name": "research-agent-server",
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
  ],
  "servers": {
    "brave-search": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "mcp/brave-search"],
      "env": {
        "BRAVE_API_KEY": "YOUR_BRAVE_API_KEY"
      }
    }
  }
}
```

### Orchestrator Agent Configuration

Create an orchestrator that delegates to other agents:

```json
{
  "agent_name": "master-orchestrator",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "server_mode": false,
  "servers": {
    "research-agent": {
      "command": "python",
      "args": ["src/agent/agent_runner.py", "--config=research_agent_config.json", "--server-mode"],
      "env": {}
    },
    "kanye": {
      "command": "npx",
      "args": ["-y", "kanye-mcp"]
    }
  }
}
```

## How It Works

### Agent Capabilities

Capabilities are high-level functions that require LLM reasoning. When a capability is called:

1. The prompt template is filled with provided arguments
2. The agent starts its own reasoning process
3. It can use any tools available to it
4. It returns the final result to the calling agent

### Example: Research Workflow

When you ask the orchestrator to research a topic:

1. The orchestrator delegates to the research agent's capability
2. The research agent uses its search tools to gather information
3. The research agent processes the results into a coherent response
4. The final result is sent back to the orchestrator and presented to you

Here's an excerpt from the logs showing this in action:

```
2025-03-19 10:17:46,252 - INFO - agent:master-orchestrator - Executing tool: research_topic
2025-03-19 10:17:46,252 - INFO - agent:master-orchestrator - With arguments: {'topic': 'quantum computing', 'focus_areas': 'recent breakthroughs'}
2025-03-19 10:17:46,261 - INFO - mcp-server-wrapper:research-agent-server - Executing as capability: research_topic
2025-03-19 10:17:46,262 - INFO - agent:research-agent - Executing capability: research_topic with arguments: {'topic': 'quantum computing', 'focus_areas': 'recent breakthroughs'}
2025-03-19 10:17:46,973 - INFO - agent:research-agent - Executing tool: brave_web_search
2025-03-19 10:17:46,973 - INFO - agent:research-agent - With arguments: {'query': 'quantum computing recent breakthroughs', 'count': 10}
2025-03-19 10:17:49,839 - INFO - agent:research-agent - Capability research_topic execution completed
```

## Architecture Details

The recursive architecture is built on the MCP (Model Context Protocol) standard and enables:

1. **Agent Hierarchy**: Agents can be arranged in a hierarchical structure where higher-level agents delegate tasks to specialized lower-level agents.
2. **Capability Delegation**: Complex tasks requiring reasoning can be delegated to specialized agents through capabilities.
3. **Tool Aggregation**: Tools from lower-level agents are automatically exposed to higher-level agents.
4. **Recursive Reasoning**: Each agent can perform its own reasoning process using its available tools. A limit to this recursion can be set.

## Running Agents in Claude Desktop

Claude Desktop supports MCP agents through its configuration system. You can configure and run your agents directly in Claude, enabling it to use your custom capabilities.

### Setup Steps

1. Locate your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add your agent configuration to the `mcpServers` section:

```json
{
  "mcpServers": {
    "research-agent": {
      "command": "/bin/bash",
      "args": ["-c", "/path/to/your/venv/bin/python /path/to/your/agent_runner.py --config=/path/to/your/agent_config.json --server-mode"],
      "env": {
        "PYTHONPATH": "/path/to/your/project",
        "PATH": "/path/to/your/venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
      }
    }
  }
}
```

### Key Components

1. **AgentServer**: Main class that manages an agent in both client and server modes, handling initialization, connection to other servers, and tool/capability discovery.
2. **MCPServerWrapper**: Wraps an Agent as an MCP server to expose its tools and capabilities through the MCP protocol.
3. **Agent**: Core agent implementation that processes user requests, executes tools, and manages capabilities.
4. **CapabilityRegistry**: Registry for agent capabilities that require LLM reasoning, responsible for loading capabilities from configuration.
5. **ToolRegistry**: Registry for all tools from MCP servers, handling discovery and registration.

### Architecture Benefits

1. **Hierarchical Composition**: Agents can use other agents' capabilities, creating a powerful composition model.
2. **Encapsulation**: Each agent encapsulates a specific domain or capability.
3. **Reasoning Delegation**: Complex tasks can be delegated to specialized agents.
4. **Tool Propagation**: Tools available to lower-level agents are accessible through capabilities to higher-level agents and with direct access.
5. **Configuration-Driven**: Define capabilities through simple configuration files without changing code.
6. **Scalability**: Add new capabilities or specialized agents without modifying existing ones.
