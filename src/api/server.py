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
    MCPTool(
        name="infer_relation",
        description="Infer the relationship between two technologies or concepts using graph traversal.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "First technology/concept name"
                },
                "target": {
                    "type": "string",
                    "description": "Second technology/concept name"
                }
            },
            "required": ["source", "target"]
        }
    ),
    MCPTool(
        name="find_path",
        description="Find connection paths between two technologies in the knowledge graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Starting technology name"
                },
                "target": {
                    "type": "string",
                    "description": "Target technology name"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum path depth (default 4)",
                    "default": 4
                }
            },
            "required": ["source", "target"]
        }
    ),
    MCPTool(
        name="recommend",
        description="Get technology recommendations based on graph relationships.",
        inputSchema={
            "type": "object",
            "properties": {
                "technology": {
                    "type": "string",
                    "description": "Base technology to get recommendations for"
                },
                "type": {
                    "type": "string",
                    "description": "Recommendation type: all, alternative, complement",
                    "enum": ["all", "alternative", "complement"],
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum recommendations (default 10)",
                    "default": 10
                }
            },
            "required": ["technology"]
        }
    ),
    MCPTool(
        name="find_similar",
        description="Find similar technologies based on category and tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "technology": {
                    "type": "string",
                    "description": "Technology to find similar ones for"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 10)",
                    "default": 10
                }
            },
            "required": ["technology"]
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
    
    elif tool_name == "infer_relation":
        from ..knowledge.inference import GraphInference
        inference = GraphInference()
        result = await inference.find_relation(
            source=args.get("source", ""),
            target=args.get("target", ""),
        )
        return {
            "query": result.query,
            "result": result.result,
            "confidence": result.confidence,
            "reasoning": result.reasoning_path,
        }
    
    elif tool_name == "find_path":
        from ..knowledge.inference import GraphInference
        inference = GraphInference()
        result = await inference.find_path(
            source=args.get("source", ""),
            target=args.get("target", ""),
            max_depth=args.get("max_depth", 4),
        )
        return {
            "query": result.query,
            "result": result.result,
            "confidence": result.confidence,
        }
    
    elif tool_name == "recommend":
        from ..knowledge.inference import GraphInference
        inference = GraphInference()
        result = await inference.recommend(
            technology=args.get("technology", ""),
            relation_type=args.get("type", "all"),
            limit=args.get("limit", 10),
        )
        return {
            "query": result.query,
            "result": result.result,
            "confidence": result.confidence,
        }
    
    elif tool_name == "find_similar":
        from ..knowledge.inference import GraphInference
        inference = GraphInference()
        result = await inference.find_similar(
            technology=args.get("technology", ""),
            limit=args.get("limit", 10),
        )
        return {
            "query": result.query,
            "result": result.result,
            "confidence": result.confidence,
        }
    
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


# ==================== Inference REST API ====================

@app.get("/knowledge/infer/relation")
async def infer_relation(source: str, target: str):
    """Find relationships between two technologies."""
    from ..knowledge.inference import GraphInference
    inference = GraphInference()
    result = await inference.find_relation(source, target)
    return {
        "query": result.query,
        "result": result.result,
        "confidence": result.confidence,
        "reasoning": result.reasoning_path,
    }


@app.get("/knowledge/infer/path")
async def find_path(source: str, target: str, max_depth: int = 4):
    """Find connection paths between technologies."""
    from ..knowledge.inference import GraphInference
    inference = GraphInference()
    result = await inference.find_path(source, target, max_depth)
    return {
        "source": source,
        "target": target,
        "paths": result.result.get("paths", []),
        "shortest": result.result.get("shortest"),
        "confidence": result.confidence,
    }


@app.get("/knowledge/recommend/{technology}")
async def recommend(technology: str, type: str = "all", limit: int = 10):
    """Get technology recommendations."""
    from ..knowledge.inference import GraphInference
    inference = GraphInference()
    result = await inference.recommend(technology, type, limit)
    return {
        "base": technology,
        "type": type,
        "recommendations": result.result.get("recommendations", []),
        "confidence": result.confidence,
    }


@app.get("/knowledge/similar/{technology}")
async def find_similar(technology: str, limit: int = 10):
    """Find similar technologies."""
    from ..knowledge.inference import GraphInference
    inference = GraphInference()
    result = await inference.find_similar(technology, limit)
    return {
        "base": technology,
        "similar": result.result.get("similar", []),
        "confidence": result.confidence,
    }


# ==================== Collection API ====================

class CollectRequest(BaseModel):
    """수집 요청 모델."""
    categories: Optional[List[str]] = None
    technologies: Optional[List[str]] = None
    assets: Optional[List[str]] = None


@app.post("/knowledge/collect")
async def collect_knowledge(request: CollectRequest):
    """
    지식 수집 트리거.
    
    Categories:
    - technology: 기술/라이브러리 정보
    - asset: 암호화폐/투자 자산
    - news: 뉴스/기사
    - concept: 개념/용어
    - person: 인물/조직
    """
    try:
        # 새로운 수집기 import (agents 패키지에서)
        import sys
        sys.path.insert(0, "/data/apps/agents/src")
        from knowledge.collectors import UnifiedCollector
        from knowledge.store import KnowledgeStore
        
        store = KnowledgeStore()
        collector = UnifiedCollector(store)
        
        results = await collector.collect_all(
            save=True,
            categories=request.categories
        )
        
        return {
            "status": "success",
            "collected": {cat: len(entities) for cat, entities in results.items()},
            "total": sum(len(e) for e in results.values()),
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Collector not available: {e}",
            "hint": "Run from agents container or install knowledge collectors"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/categories")
async def list_categories():
    """사용 가능한 카테고리 목록."""
    return {
        "categories": [
            {
                "id": "technology",
                "name": "Technology",
                "description": "프레임워크, 라이브러리, 도구 등 기술 정보",
                "examples": ["langchain", "ollama", "qdrant"]
            },
            {
                "id": "asset",
                "name": "Asset",
                "description": "암호화폐, 주식 등 투자 자산 정보",
                "examples": ["bitcoin", "ethereum", "solana"]
            },
            {
                "id": "news",
                "name": "News",
                "description": "뉴스, 기사, 공지사항",
                "sources": ["Hacker News", "CoinDesk"]
            },
            {
                "id": "concept",
                "name": "Concept",
                "description": "개념, 용어, 정의",
                "examples": ["RAG", "DeFi", "LLM"]
            },
            {
                "id": "person",
                "name": "Person/Organization",
                "description": "인물, 조직, 회사 정보",
                "examples": ["Vitalik Buterin", "OpenAI", "LangChain Inc"]
            },
        ]
    }


@app.get("/knowledge/entities/by-type/{entity_type}")
async def get_entities_by_type(entity_type: str, limit: int = 50):
    """특정 타입의 엔티티 조회."""
    graph = KnowledgeGraph()
    try:
        # Neo4j에서 타입별 조회
        query = """
        MATCH (e:Entity)
        WHERE e.entity_type = $entity_type
        RETURN e
        ORDER BY e.trust_score DESC
        LIMIT $limit
        """
        result = await graph.run_query(query, {"entity_type": entity_type, "limit": limit})
        return {"entities": result, "count": len(result)}
    except Exception as e:
        return {"entities": [], "error": str(e)}
    finally:
        await graph.disconnect()


@app.get("/knowledge/market/overview")
async def market_overview():
    """암호화폐 시장 개요."""
    try:
        import sys
        sys.path.insert(0, "/data/apps/agents/src")
        from knowledge.collectors import AssetCollector
        
        collector = AssetCollector()
        return await collector.collect_market_overview()
    except Exception as e:
        return {"error": str(e)}


# Register MCP router
app.include_router(mcp_router)


# ==================== Knowledge Graph Viewer ====================
# 시각화 페이지 (viewer.py에서 import)
try:
    from .viewer import router as viewer_router
    app.include_router(viewer_router, prefix="/knowledge")
except ImportError:
    pass

