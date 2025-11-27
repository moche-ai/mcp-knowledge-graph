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

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..config import config
from ..knowledge.graph import KnowledgeGraph
from .mcp_tools import MCP_TOOLS, MCPToolExecutor


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
    """MCP server capabilities."""
    tools: Dict[str, bool] = {"listTools": True, "call": True}
    resources: Dict[str, bool] = {"list": True, "read": True}


class MCPServerInfo(BaseModel):
    """MCP server information."""
    name: str = "mcp-knowledge-graph"
    version: str = "1.0.0"
    protocolVersion: str = "2024-11-05"
    capabilities: MCPCapabilities = Field(default_factory=MCPCapabilities)


# ==================== MCP Router ====================

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
    executor = MCPToolExecutor(graph)
    
    try:
        result = await executor.execute(tool_name, arguments)
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
    """
    사용 가능한 카테고리 목록.
    Neo4j에서 실제 사용 중인 entity_type들을 동적으로 조회합니다.
    """
    # 기본 카테고리 정의 (그룹핑용)
    CATEGORY_GROUPS = {
        "technology": {
            "name": "Technology",
            "description": "프레임워크, 라이브러리, 도구 등 기술 정보",
            "types": ["technology", "framework", "model", "service", "tool", "language", "pattern", "best_practice", "project"],
            "icon": "🔧"
        },
        "asset": {
            "name": "Asset",
            "description": "암호화폐, 주식 등 투자 자산 정보",
            "types": ["asset", "cryptocurrency", "stock", "etf", "commodity"],
            "icon": "💰"
        },
        "news": {
            "name": "News",
            "description": "뉴스, 기사, 공지사항",
            "types": ["news", "article", "research_paper", "document"],
            "icon": "📰"
        },
        "concept": {
            "name": "Concept",
            "description": "개념, 용어, 정의",
            "types": ["concept", "topic", "fact"],
            "icon": "💡"
        },
        "person": {
            "name": "Person/Organization",
            "description": "인물, 조직, 회사 정보",
            "types": ["person", "organization"],
            "icon": "👥"
        },
        "event": {
            "name": "Event",
            "description": "이벤트, 장소 정보",
            "types": ["event", "location"],
            "icon": "📅"
        },
        "product": {
            "name": "Product",
            "description": "제품, 서비스",
            "types": ["product"],
            "icon": "📦"
        },
    }
    
    # Neo4j에서 실제 사용 중인 entity_type 조회
    graph = KnowledgeGraph()
    try:
        result = await graph.run_query(
            """
            MATCH (e:Entity)
            RETURN DISTINCT e.entity_type as entity_type, count(e) as count
            ORDER BY count DESC
            """
        )
        
        # 동적으로 발견된 타입들
        discovered_types = {r["entity_type"]: r["count"] for r in result if r.get("entity_type")}
        
        # 카테고리 목록 생성 (그룹별로)
        categories = []
        used_types = set()
        
        for group_id, group_info in CATEGORY_GROUPS.items():
            group_types = group_info["types"]
            matching_types = []
            total_count = 0
            
            for t in group_types:
                if t in discovered_types:
                    matching_types.append({"type": t, "count": discovered_types[t]})
                    total_count += discovered_types[t]
                    used_types.add(t)
            
            if matching_types:
                categories.append({
                    "id": group_id,
                    "name": group_info["name"],
                    "description": group_info["description"],
                    "icon": group_info["icon"],
                    "types": matching_types,
                    "total_count": total_count
                })
        
        # 그룹에 속하지 않은 새로운 타입들 (자동 발견)
        new_types = []
        for entity_type, count in discovered_types.items():
            if entity_type and entity_type not in used_types:
                new_types.append({"type": entity_type, "count": count})
        
        if new_types:
            categories.append({
                "id": "other",
                "name": "Other",
                "description": "기타 자동 발견된 카테고리",
                "icon": "🏷️",
                "types": new_types,
                "total_count": sum(t["count"] for t in new_types)
            })
        
        # 총 엔티티 수
        total_entities = sum(c["total_count"] for c in categories)
        
        return {
            "categories": categories,
            "total_entity_types": len(discovered_types),
            "total_entities": total_entities
        }
        
    except Exception as e:
        # 에러 시 기본 정적 목록 반환
        return {
            "categories": [
                {"id": "technology", "name": "Technology", "description": "프레임워크, 라이브러리, 도구 등 기술 정보", "icon": "🔧"},
                {"id": "asset", "name": "Asset", "description": "암호화폐, 주식 등 투자 자산 정보", "icon": "💰"},
                {"id": "news", "name": "News", "description": "뉴스, 기사, 공지사항", "icon": "📰"},
                {"id": "concept", "name": "Concept", "description": "개념, 용어, 정의", "icon": "💡"},
                {"id": "person", "name": "Person/Organization", "description": "인물, 조직, 회사 정보", "icon": "👥"},
            ],
            "error": str(e)
        }
    finally:
        await graph.disconnect()


@app.get("/knowledge/entity-types")
async def list_entity_types():
    """
    모든 entity_type 목록과 개수를 반환합니다.
    프론트엔드 필터에서 사용 가능한 모든 타입을 표시합니다.
    """
    graph = KnowledgeGraph()
    try:
        result = await graph.run_query(
            """
            MATCH (e:Entity)
            WHERE e.entity_type IS NOT NULL
            RETURN DISTINCT e.entity_type as entity_type, count(e) as count
            ORDER BY count DESC
            """
        )
        
        entity_types = [
            {"type": r["entity_type"], "count": r["count"]}
            for r in result if r.get("entity_type")
        ]
        
        return {
            "entity_types": entity_types,
            "total_types": len(entity_types),
            "total_entities": sum(t["count"] for t in entity_types)
        }
    except Exception as e:
        return {"entity_types": [], "error": str(e)}
    finally:
        await graph.disconnect()


@app.get("/knowledge/entities/by-type/{entity_type}")
async def get_entities_by_type(entity_type: str, limit: int = 50):
    """특정 타입의 엔티티 조회."""
    graph = KnowledgeGraph()
    try:
        result = await graph.run_query(
            """
            MATCH (e:Entity)
            WHERE e.entity_type = $entity_type
            RETURN e
            ORDER BY e.trust_score DESC
            LIMIT $limit
            """,
            {"entity_type": entity_type, "limit": limit}
        )
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


# ==================== Register Routers ====================

app.include_router(mcp_router)

# Knowledge Graph Viewer
try:
    from .viewer import router as viewer_router
    app.include_router(viewer_router, prefix="/knowledge")
except ImportError:
    pass
