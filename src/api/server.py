"""
MCP Knowledge Graph Server

A Model Context Protocol server that provides:
- Verified knowledge search with trust scores
- Technology context with dependencies and alternatives
- Best practices and pitfall warnings
- Architecture pattern recommendations
- Reasoning-based answers (not just search results)
"""
from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..config import config
from ..knowledge.graph import KnowledgeGraph


# ==================== App Setup ====================

app = FastAPI(
    title="MCP Knowledge Graph",
    description="Verified knowledge graph with reasoning, fact-checking, and best practices",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== MCP Schema ====================

class MCPCapabilities(BaseModel):
    tools: Dict[str, bool] = {"listTools": True, "call": True}
    resources: Dict[str, bool] = {"list": True, "read": True}


class MCPServerInfo(BaseModel):
    name: str = "mcp-knowledge-graph"
    version: str = "1.0.0"
    protocolVersion: str = "2024-11-05"
    capabilities: MCPCapabilities = Field(default_factory=MCPCapabilities)


class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


# ==================== MCP Tools Definition ====================

MCP_TOOLS: List[MCPTool] = [
    MCPTool(
        name="search_knowledge",
        description="Search the knowledge graph for verified information. Returns entities with trust scores, descriptions, and metadata.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keyword or natural language)"
                },
                "min_trust": {
                    "type": "number",
                    "description": "Minimum trust score (0-1, default 0.7)",
                    "default": 0.7
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    ),
    MCPTool(
        name="get_context",
        description="Get complete context for a topic including dependencies, alternatives, integrations, and installation instructions.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic name to get context for"
                }
            },
            "required": ["topic"]
        }
    ),
    MCPTool(
        name="get_dependencies",
        description="Get the dependency chain for a technology. Useful for determining installation order.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Technology/library name"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum traversal depth (default 3)",
                    "default": 3
                }
            },
            "required": ["name"]
        }
    ),
    MCPTool(
        name="get_alternatives",
        description="Get alternative technologies/tools for comparison.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Technology name to find alternatives for"
                }
            },
            "required": ["name"]
        }
    ),
    MCPTool(
        name="get_best_practices",
        description="Get best practices, common pitfalls, and recommendations for a technology.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Technology name"
                }
            },
            "required": ["name"]
        }
    ),
    MCPTool(
        name="get_stats",
        description="Get knowledge graph statistics including entity counts, relation counts, and trust score distribution.",
        inputSchema={
            "type": "object",
            "properties": {},
        }
    ),
]


# ==================== MCP Router ====================

from fastapi import APIRouter
mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])


@mcp_router.get("/info")
async def mcp_info():
    """Get MCP server information."""
    return MCPServerInfo().model_dump()


@mcp_router.get("/tools/list")
async def list_tools():
    """List available MCP tools."""
    return {"tools": [tool.model_dump() for tool in MCP_TOOLS]}


@mcp_router.post("/tools/call")
async def call_tool(request: Request):
    """Call an MCP tool."""
    body = await request.json()
    tool_name = body.get("name")
    arguments = body.get("arguments", {})
    
    graph = KnowledgeGraph()
    
    try:
        result = await _execute_tool(graph, tool_name, arguments)
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, (dict, list)) else str(result)
            }]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True
        }
    finally:
        await graph.disconnect()


async def _execute_tool(graph: KnowledgeGraph, tool_name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool and return results."""
    
    if tool_name == "search_knowledge":
        return await graph.search_entities(
            query=args.get("query", ""),
            min_trust=args.get("min_trust", 0.7),
            limit=args.get("limit", 10),
        )
    
    elif tool_name == "get_context":
        topic = args.get("topic", "")
        entity = await graph.get_entity(topic)
        relations = await graph.get_relations(topic)
        
        return {
            "entity": entity,
            "dependencies": relations.get("depends_on", []),
            "integrations": relations.get("integrates_with", []),
            "alternatives": relations.get("alternative_to", []),
        }
    
    elif tool_name == "get_dependencies":
        return await graph.get_dependency_chain(
            name=args.get("name", ""),
            max_depth=args.get("max_depth", 3),
        )
    
    elif tool_name == "get_alternatives":
        relations = await graph.get_relations(args.get("name", ""))
        return relations.get("alternative_to", [])
    
    elif tool_name == "get_best_practices":
        # Return stored best practices or empty
        entity = await graph.get_entity(args.get("name", ""))
        if entity:
            props = entity.get("properties", {})
            return {
                "name": entity.get("name"),
                "key_features": props.get("key_features", []),
                "use_cases": props.get("use_cases", []),
                "limitations": props.get("limitations", []),
                "installation": props.get("installation", ""),
            }
        return {"message": "No best practices found for this topic"}
    
    elif tool_name == "get_stats":
        return await graph.get_stats()
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


@mcp_router.get("/resources/list")
async def list_resources():
    """List available MCP resources."""
    return {
        "resources": [
            {
                "uri": "knowledge://stats",
                "name": "Knowledge Graph Statistics",
                "description": "Statistics about the knowledge graph",
                "mimeType": "application/json"
            },
            {
                "uri": "knowledge://entities",
                "name": "Entity List",
                "description": "List of all entities in the knowledge graph",
                "mimeType": "application/json"
            },
        ]
    }


@mcp_router.post("/resources/read")
async def read_resource(request: Request):
    """Read an MCP resource."""
    body = await request.json()
    uri = body.get("uri", "")
    
    graph = KnowledgeGraph()
    
    try:
        if uri == "knowledge://stats":
            result = await graph.get_stats()
        elif uri == "knowledge://entities":
            result = await graph.search_entities("", min_trust=0.0, limit=100)
        else:
            result = {"error": f"Unknown resource: {uri}"}
        
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(result, ensure_ascii=False, indent=2)
            }]
        }
    finally:
        await graph.disconnect()


@mcp_router.get("/sse")
async def mcp_sse(request: Request):
    """SSE endpoint for MCP streaming."""
    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
        yield f"event: server_info\ndata: {json.dumps(MCPServerInfo().model_dump())}\n\n"
        
        while True:
            if await request.is_disconnected():
                break
            yield f"event: ping\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(30)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ==================== REST API Endpoints ====================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/knowledge/stats")
async def knowledge_stats():
    """Get knowledge graph statistics."""
    graph = KnowledgeGraph()
    try:
        return await graph.get_stats()
    finally:
        await graph.disconnect()


@app.get("/knowledge/search")
async def knowledge_search(q: str, min_trust: float = 0.7, limit: int = 10):
    """Search the knowledge graph."""
    graph = KnowledgeGraph()
    try:
        return await graph.search_entities(q, min_trust, limit)
    finally:
        await graph.disconnect()


@app.get("/knowledge/context/{name}")
async def knowledge_context(name: str):
    """Get context for a topic."""
    graph = KnowledgeGraph()
    try:
        entity = await graph.get_entity(name)
        relations = await graph.get_relations(name)
        deps = await graph.get_dependency_chain(name)
        
        return {
            "entity": entity,
            "relations": relations,
            "dependency_chain": deps,
        }
    finally:
        await graph.disconnect()


# Register MCP router
app.include_router(mcp_router)

