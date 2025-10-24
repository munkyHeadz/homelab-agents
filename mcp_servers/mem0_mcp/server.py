"""
Mem0 Memory MCP Server

Provides MCP tools for agent memory management using Mem0:
- Store and retrieve agent memories
- Search memories semantically
- Update and delete memories
- Memory categorization (user, agent, session)
- Memory metadata and tagging
"""

import os
from typing import List, Dict, Any, Optional
from mem0 import Memory
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB_MEMORY", "agent_memory")
POSTGRES_USER = os.getenv("POSTGRES_USER_MEMORY", "mem0_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD_MEMORY", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Initialize MCP server
server = Server("mem0-mcp")

# Initialize Mem0 with Qdrant (local vector store - no PostgreSQL needed for now)
# TODO: Set up pgvector extension in PostgreSQL and switch back
mem0_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333,
        }
    },
    "llm": {
        "provider": "anthropic",
        "config": {
            "api_key": ANTHROPIC_API_KEY,
            "model": "claude-3-5-haiku-20241022",  # Use fast model for memory ops
        }
    },
    "embedder": {
        "provider": "openai",  # Anthropic not supported for embeddings, use OpenAI
        "config": {
            "model": "text-embedding-3-small",
            "api_key": OPENAI_API_KEY,
        }
    }
}

memory = Memory.from_config(mem0_config)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Mem0 memory tools"""
    return [
        types.Tool(
            name="add_memory",
            description="Add a new memory for an agent or user",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content to store"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID associated with this memory"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID associated with this memory (optional)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (tags, category, etc.)"
                    }
                },
                "required": ["content", "user_id"]
            }
        ),
        types.Tool(
            name="search_memories",
            description="Search memories semantically using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query in natural language"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Filter by user ID"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Filter by agent ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_all_memories",
            description="Get all memories for a user or agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to retrieve memories for"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to retrieve memories for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return",
                        "default": 50
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="update_memory",
            description="Update an existing memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to update"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the memory"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Updated metadata"
                    }
                },
                "required": ["memory_id", "content"]
            }
        ),
        types.Tool(
            name="delete_memory",
            description="Delete a memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to delete"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        types.Tool(
            name="delete_all_memories",
            description="Delete all memories for a user or agent (use with caution!)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to delete memories for"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to delete memories for"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_memory_history",
            description="Get the history of a specific memory (all versions)",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory ID"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        types.Tool(
            name="summarize_memories",
            description="Get an AI-generated summary of all memories for a context",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to summarize memories for"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to summarize memories for"
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    try:
        if name == "add_memory":
            content = arguments["content"]
            user_id = arguments["user_id"]
            agent_id = arguments.get("agent_id")
            metadata = arguments.get("metadata", {})

            # Build filters
            filters = {"user_id": user_id}
            if agent_id:
                filters["agent_id"] = agent_id

            # Add memory
            result = memory.add(
                content,
                user_id=user_id,
                agent_id=agent_id,
                metadata=metadata
            )

            return [types.TextContent(
                type="text",
                text=f"✅ Memory added successfully\\n" +
                     f"Memory ID: {result['id']}\\n" +
                     f"Content: {content}\\n" +
                     f"User: {user_id}" +
                     (f"\\nAgent: {agent_id}" if agent_id else "")
            )]

        elif name == "search_memories":
            query = arguments["query"]
            user_id = arguments.get("user_id")
            agent_id = arguments.get("agent_id")
            limit = arguments.get("limit", 10)

            # Build filters
            filters = {}
            if user_id:
                filters["user_id"] = user_id
            if agent_id:
                filters["agent_id"] = agent_id

            # Search memories
            results = memory.search(
                query,
                user_id=user_id,
                agent_id=agent_id,
                limit=limit
            )

            if not results:
                return [types.TextContent(
                    type="text",
                    text=f"No memories found for query: '{query}'"
                )]

            output = f"Found {len(results)} memories for '{query}':\\n\\n"
            for idx, mem in enumerate(results, 1):
                output += f"{idx}. {mem['memory']}\\n"
                output += f"   ID: {mem['id']}\\n"
                output += f"   Score: {mem.get('score', 0):.3f}\\n"
                if mem.get('metadata'):
                    output += f"   Metadata: {mem['metadata']}\\n"
                output += "\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_all_memories":
            user_id = arguments.get("user_id")
            agent_id = arguments.get("agent_id")
            limit = arguments.get("limit", 50)

            # Get all memories
            memories = memory.get_all(
                user_id=user_id,
                agent_id=agent_id,
                limit=limit
            )

            if not memories:
                return [types.TextContent(
                    type="text",
                    text="No memories found"
                )]

            output = f"Found {len(memories)} memories:\\n\\n"
            for idx, mem in enumerate(memories, 1):
                output += f"{idx}. {mem['memory']}\\n"
                output += f"   ID: {mem['id']}\\n"
                output += f"   Created: {mem.get('created_at', 'N/A')}\\n"
                if mem.get('metadata'):
                    output += f"   Metadata: {mem['metadata']}\\n"
                output += "\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "update_memory":
            memory_id = arguments["memory_id"]
            content = arguments["content"]
            metadata = arguments.get("metadata")

            # Update memory
            result = memory.update(
                memory_id,
                content=content,
                metadata=metadata
            )

            return [types.TextContent(
                type="text",
                text=f"✅ Memory {memory_id} updated successfully\\n" +
                     f"New content: {content}"
            )]

        elif name == "delete_memory":
            memory_id = arguments["memory_id"]

            # Delete memory
            memory.delete(memory_id)

            return [types.TextContent(
                type="text",
                text=f"✅ Memory {memory_id} deleted successfully"
            )]

        elif name == "delete_all_memories":
            user_id = arguments.get("user_id")
            agent_id = arguments.get("agent_id")

            if not user_id and not agent_id:
                return [types.TextContent(
                    type="text",
                    text="⚠️ Error: Must provide either user_id or agent_id"
                )]

            # Delete all memories
            memory.delete_all(
                user_id=user_id,
                agent_id=agent_id
            )

            context = f"user {user_id}" if user_id else f"agent {agent_id}"
            return [types.TextContent(
                type="text",
                text=f"⚠️ All memories deleted for {context}"
            )]

        elif name == "get_memory_history":
            memory_id = arguments["memory_id"]

            # Get memory history
            history = memory.history(memory_id)

            if not history:
                return [types.TextContent(
                    type="text",
                    text=f"No history found for memory {memory_id}"
                )]

            output = f"Memory History for {memory_id}:\\n\\n"
            for idx, version in enumerate(history, 1):
                output += f"Version {idx}:\\n"
                output += f"  Content: {version['memory']}\\n"
                output += f"  Updated: {version.get('updated_at', 'N/A')}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "summarize_memories":
            user_id = arguments.get("user_id")
            agent_id = arguments.get("agent_id")

            # Get all memories first
            memories = memory.get_all(
                user_id=user_id,
                agent_id=agent_id
            )

            if not memories:
                return [types.TextContent(
                    type="text",
                    text="No memories to summarize"
                )]

            # Concatenate all memory contents
            all_memories = "\\n".join([mem['memory'] for mem in memories])

            # Use Mem0's LLM to generate summary
            from anthropic import Anthropic
            client = Anthropic(api_key=ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"Summarize the following memories concisely, highlighting key patterns and important information:\\n\\n{all_memories}"
                }]
            )

            summary = response.content[0].text

            context = f"user {user_id}" if user_id else f"agent {agent_id}"
            return [types.TextContent(
                type="text",
                text=f"Memory Summary for {context}:\\n\\n{summary}\\n\\n" +
                     f"Total memories: {len(memories)}"
            )]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mem0",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
