"""MCP Tool Definitions and Handlers."""
from __future__ import annotations

import json
from typing import Any, Dict, List
from pydantic import BaseModel, Field


# ==================== MCP Tool Schema ====================

class MCPTool(BaseModel):
    """MCP Tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


# ==================== Tool Definitions ====================

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


# ==================== Tool Executor ====================

class MCPToolExecutor:
    """Executes MCP tools against the knowledge graph."""
    
    def __init__(self, graph):
        """
        Initialize executor.
        
        Args:
            graph: KnowledgeGraph instance
        """
        self.graph = graph
    
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a tool and return results.
        
        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments
            
        Returns:
            Tool execution result
        """
        handler = getattr(self, f"_handle_{tool_name}", None)
        if handler:
            return await handler(args)
        raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _handle_search_knowledge(self, args: Dict[str, Any]) -> Any:
        """Search knowledge graph."""
        return await self.graph.search_entities(
            query=args.get("query", ""),
            min_trust=args.get("min_trust", 0.7),
            limit=args.get("limit", 10),
        )
    
    async def _handle_get_context(self, args: Dict[str, Any]) -> Any:
        """Get topic context."""
        topic = args.get("topic", "")
        entity = await self.graph.get_entity(topic)
        relations = await self.graph.get_relations(topic)
        
        return {
            "entity": entity,
            "dependencies": relations.get("depends_on", []),
            "integrations": relations.get("integrates_with", []),
            "alternatives": relations.get("alternative_to", []),
        }
    
    async def _handle_get_dependencies(self, args: Dict[str, Any]) -> Any:
        """Get dependency chain."""
        return await self.graph.get_dependency_chain(
            name=args.get("name", ""),
            max_depth=args.get("max_depth", 3),
        )
    
    async def _handle_get_alternatives(self, args: Dict[str, Any]) -> Any:
        """Get alternatives."""
        relations = await self.graph.get_relations(args.get("name", ""))
        return relations.get("alternative_to", [])
    
    async def _handle_get_best_practices(self, args: Dict[str, Any]) -> Any:
        """Get best practices."""
        entity = await self.graph.get_entity(args.get("name", ""))
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
    
    async def _handle_get_stats(self, args: Dict[str, Any]) -> Any:
        """Get graph statistics."""
        return await self.graph.get_stats()
    
    async def _handle_infer_relation(self, args: Dict[str, Any]) -> Any:
        """Infer relation between entities."""
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
    
    async def _handle_find_path(self, args: Dict[str, Any]) -> Any:
        """Find path between entities."""
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
    
    async def _handle_recommend(self, args: Dict[str, Any]) -> Any:
        """Get recommendations."""
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
    
    async def _handle_find_similar(self, args: Dict[str, Any]) -> Any:
        """Find similar technologies."""
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


