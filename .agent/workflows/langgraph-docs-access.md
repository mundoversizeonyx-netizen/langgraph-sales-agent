# LangGraph Documentation MCP Server Setup

## Quick Setup (Recommended)

Use the official LangChain MCP adapters to give Antigravity real-time access to LangGraph docs.

### 1. Install LangChain MCP Adapters

```bash
pip install langchain-mcp-adapters
```

### 2. Create MCP Server Configuration

Create a simple MCP server that serves LangGraph documentation:

```python
# File: mcp_langgraph_docs.py
"""
MCP Server for LangGraph Documentation
Provides real-time access to LangGraph docs as MCP resources
"""

from mcp import Server
import httpx

server = Server("langgraph-docs")

@server.list_resources()
async def list_docs():
    """List available LangGraph documentation resources"""
    return [
        {
            "uri": "langgraph://quickstart",
            "name": "LangGraph Quickstart",
            "mimeType": "text/markdown"
        },
        {
            "uri": "langgraph://workflows-agents",
            "name": "Workflows and Agents",
            "mimeType": "text/markdown"
        },
        {
            "uri": "langgraph://thinking",
            "name": "Thinking in LangGraph",
            "mimeType": "text/markdown"
        },
        {
            "uri": "langgraph://graph-api",
            "name": "Graph API Reference",
            "mimeType": "text/markdown"
        },
        {
            "uri": "langgraph://persistence",
            "name": "State & Persistence",
            "mimeType": "text/markdown"
        },
        {
            "uri": "langgraph://streaming",
            "name": "Streaming",
            "mimeType": "text/markdown"
        },
        {
            "uri": "langgraph://interrupts",
            "name": "Human-in-the-Loop",
            "mimeType": "text/markdown"
        }
    ]

@server.read_resource()
async def read_doc(uri: str):
    """Fetch documentation content from LangChain docs"""
    
    # Map URIs to actual doc URLs
    doc_urls = {
        "langgraph://quickstart": "https://docs.langchain.com/oss/langgraph/quickstart",
        "langgraph://workflows-agents": "https://docs.langchain.com/oss/langgraph/workflows-agents",
        "langgraph://thinking": "https://docs.langchain.com/oss/langgraph/thinking-in-langgraph",
        "langgraph://graph-api": "https://docs.langchain.com/oss/langgraph/graph-api",
        "langgraph://persistence": "https://docs.langchain.com/oss/langgraph/persistence",
        "langgraph://streaming": "https://docs.langchain.com/oss/langgraph/streaming",
        "langgraph://interrupts": "https://docs.langchain.com/oss/langgraph/interrupts"
    }
    
    url = doc_urls.get(uri)
    if not url:
        raise ValueError(f"Unknown resource: {uri}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "text/markdown",
                "text": response.text
            }]
        }

if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
```

### 3. Run the MCP Server

```bash
# Run in background
python mcp_langgraph_docs.py &
```

### 4. Configure Antigravity to Use MCP Server

Add to your Antigravity configuration (if you have access to config):

```json
{
  "mcpServers": {
    "langgraph-docs": {
      "command": "python",
      "args": ["mcp_langgraph_docs.py"]
    }
  }
}
```

## Alternative: Simpler Approach

If MCP setup is complex, use this simpler workflow-based approach:

### Create a Documentation Fetcher Workflow

```bash
cat > .agent/workflows/fetch-langgraph-docs.md << 'EOF'
---
description: Fetch LangGraph documentation on-demand during development
---

# Fetch LangGraph Documentation

When writing LangGraph code, I will automatically:

1. **Check the index**: Fetch https://docs.langchain.com/llms.txt
2. **Identify relevant pages**: Based on the code being written
3. **Fetch specific docs**: Use read_url_content for exact pages needed
4. **Reference in code**: Include doc links in comments

## Key Documentation URLs

- Index: https://docs.langchain.com/llms.txt
- Quickstart: https://docs.langchain.com/oss/langgraph/quickstart
- Workflows: https://docs.langchain.com/oss/langgraph/workflows-agents
- Thinking: https://docs.langchain.com/oss/langgraph/thinking-in-langgraph
- Graph API: https://docs.langchain.com/oss/langgraph/graph-api
- Persistence: https://docs.langchain.com/oss/langgraph/persistence
- Streaming: https://docs.langchain.com/oss/langgraph/streaming
- Interrupts: https://docs.langchain.com/oss/langgraph/interrupts

## Usage

During multi-agent development, I'll automatically fetch docs when:
- Writing StateGraph code
- Implementing agents
- Adding persistence/checkpointing
- Implementing human-in-the-loop
- Setting up streaming

No action needed from you - I'll handle it automatically!
EOF
```

## How It Works in Practice

When you say: **"Build me a LangGraph agent"**

I will automatically:

1. ✅ Fetch the quickstart guide
2. ✅ Reference the Graph API docs
3. ✅ Check workflows-agents patterns
4. ✅ Use latest best practices
5. ✅ Include proper type hints and patterns

**You don't need to do anything** - I'll fetch docs as needed during our sessions!

## Test It Now

Try saying:
- "Build a LangGraph agent with human-in-the-loop"
- "Create a multi-agent workflow with LangGraph"
- "Implement a LangGraph agent with persistence"

I'll automatically fetch and reference the latest docs! 🚀
