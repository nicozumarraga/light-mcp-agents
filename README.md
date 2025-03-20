# Recursive MCP Agent Architecture

This project implements a recursive agent architecture that allows agents to function both as MCP clients and servers. This creates a hierarchical composition model where agents can leverage the capabilities of other agents through a powerful delegation mechanism.

## Architecture Overview

The recursive architecture is built on the MCP (Model Context Protocol) standard and enables:

1. **Agent Hierarchy**: Agents can be arranged in a hierarchical structure where higher-level agents delegate tasks to specialized lower-level agents.
2. **Capability Delegation**: Complex tasks requiring reasoning can be delegated to specialized agents through capabilities.
3. **Tool Aggregation**: Tools from lower-level agents are automatically exposed to higher-level agents.
4. **Recursive Reasoning**: Each agent can perform its own reasoning process using its available tools.

<img width="725" alt="light-mcp-agents-diagram" src="https://github.com/user-attachments/assets/9a69e2da-403e-40e3-9f6f-4cf484dc7444" />


## Key Components

1. **AgentServer**: Main class that manages an agent in both client and server modes, handling initialization, connection to other servers, and tool/capability discovery.
2. **MCPServerWrapper**: Wraps an Agent as an MCP server to expose its tools and capabilities through the MCP protocol.
3. **Agent**: Core agent implementation that processes user requests, executes tools, and manages capabilities.
4. **CapabilityRegistry**: Registry for agent capabilities that require LLM reasoning, responsible for loading capabilities from configuration.
5. **ToolRegistry**: Registry for all tools from MCP servers, handling discovery and registration.

## Technical Deep Dive

### Agent Initialization Process

1. **Configuration Loading**: The `AgentServer` loads configuration from a JSON file.
2. **LLM Client Creation**: A language model client is created based on the configuration.
3. **Server Connections**: The agent connects to all specified servers in the configuration.
4. **Tool Discovery**: The agent queries all connected servers for their available tools.
5. **Capability Loading**: Capabilities are loaded from the configuration file.
6. **Server Mode Setup**: If running in server mode, the `MCPServerWrapper` is initialized to expose the agent's tools and capabilities.

### Capability Execution Flow

When a capability is called, the following steps occur:

1. **Request Reception**: The `MCPServerWrapper` receives a tool call for a capability.
2. **Capability Identification**: The wrapper identifies this as a capability (not a regular tool).
3. **Prompt Formation**: The capability's prompt template is filled with the provided arguments.
4. **Reasoning Initiation**: The agent starts its own reasoning process with the formatted prompt.
5. **Tool Usage**: The agent can use any tools available to it during the reasoning process.
6. **Result Compilation**: After completing its reasoning, the agent compiles a final result.
7. **Response Return**: The result is returned to the calling agent as a tool response.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-agents.git
cd mcp-agents

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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
    },
    {
      "name": "research_topic",
      "description": "Research a topic and provide key information",
      "input_schema": {
        "type": "object",
        "properties": {
          "topic": {
            "type": "string",
            "description": "The topic to research"
          },
          "focus_areas": {
            "type": "string",
            "description": "Specific aspects to focus on",
            "default": "main concepts, history, and applications"
          }
        },
        "required": ["topic"]
      },
      "prompt_template": "Research the topic '{topic}' and provide key information. Focus on these aspects: {focus_areas}. Use the search tools to find relevant information."
    }
  ],
  "servers": {
    "brave-search": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "BRAVE_API_KEY",
        "mcp/brave-search"
      ],
      "env": {
        "BRAVE_API_KEY": "YOUR_BRAVE_API_KEY"
      }
    }
  }
}
```

### Orchestrator Agent

For an orchestrator agent that connects to other agents:

```json
{
  "agent_name": "master-orchestrator",
  "llm_provider": "groq",
  "llm_api_key": "YOUR_API_KEY_HERE",
  "server_mode": false,
  "servers": {
    "research-agent": {
      "command": "python",
      "args": ["agent_runner.py", "--config=research_agent_config.json", "--server-mode"],
      "env": {}
    },
    "kanye": {
      "command": "npx",
      "args": ["-y", "kanye-mcp"]
    }
  }
}
```

## Running Example Agents

The repository includes example agents in the `examples/` directory that you can run to get started.

### Quick Start with Example Agents

Run one of the built-in example agents:

```bash
# Run the base agent example (simple client agent)
python src/agent/agent_runner.py --config examples/base_agent/base_agent_config.json

# Run the orchestrator-researcher example (demonstrates agent hierarchy)
python src/agent/agent_runner.py --config examples/orchestrator_researcher/research_agent_config.json

# In a separate terminal run the orchestrator
python src/agent/agent_runner.py --config examples/orchestrator_researcher/master_orchestrator_config.json
```

### Understanding Example Agents

1. **Base Agent** (`examples/base_agent/`)
   - A simple agent that connects to external tool servers
   - Demonstrates basic agent functionality
   - Configured to use tools like web search

2. **Orchestrator-Researcher** (`examples/orchestrator_researcher/`)
   - Demonstrates a hierarchical agent structure
   - An orchestrator agent that delegates to a specialized research agent
   - Shows how capabilities can be shared between agents

### Running Examples with Additional Options

You can also run the examples with additional configuration options:

```bash
# Run base agent in server mode (makes it available to other agents)
./run_agent.py --example base_agent --server-mode

# Run with a custom server name
./run_agent.py --example base_agent --server-mode --server-name "my-custom-agent"

# Run using a specific config file path
./run_agent.py --config examples/base_agent/base_agent_config.json
```

### Testing Your Setup

After installation, verify your setup by running the base agent:

```bash
# Run the base agent in interactive mode
./run_agent.py --example base_agent

# If successful, you'll be able to chat with the agent and use its tools
```

### Troubleshooting Example Agents

If you encounter issues running the examples:

1. Check that your LLM API keys are properly configured
2. Make sure any external tool servers (like search tools) are accessible
3. Verify that Python can find the modules (the src directory should be in your Python path)
4. Check the logs for any specific error messages

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

### Example: Quantum Computing Research

Let's walk through a real example of how the recursive agent architecture works, based on a test run:

1. Start a specialized research agent with capabilities in server mode:
   ```bash
   python agent_runner.py --config=research_agent_config.json --server-mode
   ```

2. Start the orchestrator that connects to this agent:
   ```bash
   python agent_runner.py --config=master_orchestrator_config.json
   ```

3. Ask the orchestrator to research quantum computing:
   ```
   You: Can you research quantum computing for me? Focus on recent breakthroughs.
   ```

4. **What happens behind the scenes:**
   - The master orchestrator receives the request
   - It decides to use the "research_topic" capability from the research agent
   - It calls this capability with arguments: `{'topic': 'quantum computing', 'focus_areas': 'recent breakthroughs'}`
   - The research agent receives this request and starts its own reasoning process
   - The research agent decides to use its "brave_web_search" tool to gather information
   - The search tool returns results about quantum computing breakthroughs
   - The research agent processes these results into a coherent response
   - The final result is sent back to the master orchestrator
   - The master orchestrator presents this information to you

5. You receive a comprehensive response that includes recent breakthroughs in quantum computing from Microsoft, Google, IBM, and other research organizations.

### Logs From a Test Run

Here's an excerpt from the logs showing how the architecture works in practice:

```
2025-03-19 10:17:46,252 - INFO - agent:master-orchestrator - Executing tool: research_topic
2025-03-19 10:17:46,252 - INFO - agent:master-orchestrator - With arguments: {'topic': 'quantum computing', 'focus_areas': 'recent breakthroughs'}
2025-03-19 10:17:46,261 - INFO - mcp-server-wrapper:research-agent-server - Executing as capability: research_topic
2025-03-19 10:17:46,262 - INFO - agent:research-agent - Executing capability: research_topic with arguments: {'topic': 'quantum computing', 'focus_areas': 'recent breakthroughs'}
2025-03-19 10:17:46,973 - INFO - agent:research-agent - Executing tool: brave_web_search
2025-03-19 10:17:46,973 - INFO - agent:research-agent - With arguments: {'query': 'quantum computing recent breakthroughs', 'count': 10}
2025-03-19 10:17:49,839 - INFO - agent:research-agent - Capability research_topic execution completed
```

## Architecture Benefits

1. **Hierarchical Composition**: Agents can use other agents' capabilities, creating a powerful composition model.
2. **Encapsulation**: Each agent encapsulates a specific domain or capability, promoting better separation of concerns.
3. **Reasoning Delegation**: Complex tasks can be delegated to specialized agents, allowing for more focused reasoning.
4. **Tool Propagation**: Tools available to lower-level agents are accessible through capabilities to higher-level agents.
5. **Configuration-Driven**: Define capabilities through simple configuration files without changing code.
6. **Scalability**: Add new capabilities or specialized agents without modifying existing ones.

## Creating a Multi-Agent System

To build your own multi-agent system:

1. **Define Specialized Agents**: Create configuration files for agents with specific capabilities (research, coding, data analysis, etc.)
2. **Define an Orchestrator**: Create a configuration file for a high-level orchestrator agent that connects to specialized agents
3. **Start the Specialized Agents**: Run each specialized agent in server mode
4. **Start the Orchestrator**: Run the orchestrator agent in client mode
5. **Interact with the System**: Give tasks to the orchestrator, which will delegate to specialized agents as needed

## Best Practices

1. **Design Clear Capabilities**: Each capability should have a focused purpose and clear prompt template
2. **Use Appropriate Tools**: Ensure each agent has the tools it needs for its specialized domain
3. **Test Capability Performance**: Validate that capabilities produce good results across various inputs
4. **Monitor Agent Interactions**: Use the logs to understand and debug the delegation process
5. **Optimize Prompt Templates**: Refine capability prompt templates to improve agent reasoning

## Troubleshooting

If you encounter issues:

1. **Check Connections**: Ensure all agent servers are running and properly connected
2. **Examine Logs**: Look at the logs to see where in the process an error might be occurring
3. **Validate Configurations**: Make sure configuration files are properly formatted
4. **Test Individual Agents**: Test each agent individually before integrating them
5. **Verify API Keys**: Ensure all necessary API keys (LLM providers, search services, etc.) are valid
