"""
Knowledge Graph Inference Engine (Public Version)

Graph-based inference only (no LLM dependency):
1. Relation inference - Find direct/indirect relations in the graph
2. Path finding - Connection paths between two concepts
3. Recommendations - Relationship-based technology recommendations
4. Similarity - Category/tag-based similar technologies

Note: LLM-based inference requires separate configuration (set LLM_URL env var)
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .graph import KnowledgeGraph


@dataclass
class InferenceResult:
    """Inference result container."""
    query: str
    result: Any
    confidence: float
    reasoning_path: List[str]


class GraphInference:
    """
    Graph-based inference engine.
    
    Performs inference using Neo4j graph only, without LLM dependency.
    """
    
    def __init__(self):
        self.graph = KnowledgeGraph()
    
    async def find_relation(
        self,
        source: str,
        target: str,
    ) -> InferenceResult:
        """Find relations between two concepts."""
        reasoning = []
        
        await self.graph.connect()
        
        try:
            # Direct relations
            direct = await self._find_direct(source, target)
            reasoning.append(f"Direct relations: {len(direct)}")
            
            # Indirect relations (1-hop)
            indirect = await self._find_indirect(source, target)
            reasoning.append(f"Indirect relations (1-hop): {len(indirect)}")
            
            confidence = 0.9 if direct else (0.6 if indirect else 0.2)
            
            return InferenceResult(
                query=f"{source} → {target}",
                result={
                    "source": source,
                    "target": target,
                    "direct_relations": direct,
                    "indirect_relations": indirect,
                    "relationship_exists": bool(direct or indirect),
                },
                confidence=confidence,
                reasoning_path=reasoning,
            )
        finally:
            await self.graph.disconnect()
    
    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 4,
    ) -> InferenceResult:
        """Find paths between two concepts."""
        await self.graph.connect()
        
        try:
            paths = []
            
            if self.graph._driver:
                async with self.graph._driver.session() as session:
                    result = await session.run("""
                        MATCH path = shortestPath(
                            (a:Entity)-[*1..4]-(b:Entity)
                        )
                        WHERE toLower(a.name) CONTAINS toLower($source)
                          AND toLower(b.name) CONTAINS toLower($target)
                        RETURN path, length(path) as length
                        LIMIT 5
                    """, {"source": source, "target": target})
                    
                    async for record in result:
                        path_data = record["path"]
                        nodes = [node["name"] for node in path_data.nodes]
                        rels = [rel.type for rel in path_data.relationships]
                        paths.append({
                            "nodes": nodes,
                            "relations": rels,
                            "length": record["length"],
                        })
            
            return InferenceResult(
                query=f"Path: {source} → {target}",
                result={
                    "source": source,
                    "target": target,
                    "paths": paths,
                    "shortest": paths[0] if paths else None,
                },
                confidence=0.95 if paths else 0.1,
                reasoning_path=[f"Found {len(paths)} paths"],
            )
        finally:
            await self.graph.disconnect()
    
    async def recommend(
        self,
        technology: str,
        relation_type: str = "all",  # all, alternative, complement
        limit: int = 10,
    ) -> InferenceResult:
        """Get related technology recommendations."""
        await self.graph.connect()
        
        try:
            recommendations = []
            
            if self.graph._driver:
                async with self.graph._driver.session() as session:
                    # Relation type filter
                    if relation_type == "alternative":
                        rel_filter = "type(r) = 'alternative_to'"
                    elif relation_type == "complement":
                        rel_filter = "type(r) IN ['integrates_with', 'depends_on']"
                    else:
                        rel_filter = "true"
                    
                    result = await session.run(f"""
                        MATCH (a:Entity)-[r]-(b:Entity)
                        WHERE toLower(a.name) CONTAINS toLower($name)
                          AND {rel_filter}
                        RETURN DISTINCT b.name as name, b.description as description,
                               b.trust_score as trust_score, type(r) as relation
                        ORDER BY b.trust_score DESC
                        LIMIT $limit
                    """, {"name": technology, "limit": limit})
                    
                    async for record in result:
                        recommendations.append({
                            "name": record["name"],
                            "description": record["description"],
                            "trust_score": record["trust_score"],
                            "relation": record["relation"],
                        })
            
            return InferenceResult(
                query=f"Recommend for: {technology}",
                result={
                    "base": technology,
                    "type": relation_type,
                    "recommendations": recommendations,
                },
                confidence=0.8 if recommendations else 0.2,
                reasoning_path=[f"Found {len(recommendations)} related technologies"],
            )
        finally:
            await self.graph.disconnect()
    
    async def find_similar(
        self,
        technology: str,
        limit: int = 10,
    ) -> InferenceResult:
        """Find similar technologies (same category/tags)."""
        await self.graph.connect()
        
        try:
            similar = []
            
            if self.graph._driver:
                async with self.graph._driver.session() as session:
                    # 먼저 기준 기술의 타입과 태그 확인
                    base_result = await session.run("""
                        MATCH (e:Entity)
                        WHERE toLower(e.name) CONTAINS toLower($name)
                        RETURN e.entity_type as type, e.tags as tags
                        LIMIT 1
                    """, {"name": technology})
                    
                    base_record = await base_result.single()
                    
                    if base_record:
                        entity_type = base_record["type"]
                        tags = base_record["tags"] or []
                        
                        # Find other technologies of the same type
                        result = await session.run("""
                            MATCH (e:Entity)
                            WHERE e.entity_type = $type 
                              AND NOT toLower(e.name) CONTAINS toLower($name)
                            RETURN e.name as name, e.description as description,
                                   e.trust_score as trust_score, e.tags as tags
                            ORDER BY e.trust_score DESC
                            LIMIT $limit
                        """, {"type": entity_type, "name": technology, "limit": limit})
                        
                        async for record in result:
                            other_tags = record["tags"] or []
                            overlap = len(set(tags) & set(other_tags))
                            similarity = overlap / max(len(tags), len(other_tags), 1)
                            
                            similar.append({
                                "name": record["name"],
                                "description": record["description"],
                                "trust_score": record["trust_score"],
                                "similarity": round(similarity, 2),
                            })
                        
                        similar.sort(key=lambda x: x["similarity"], reverse=True)
            
            return InferenceResult(
                query=f"Similar to: {technology}",
                result={
                    "base": technology,
                    "similar": similar,
                },
                confidence=0.7 if similar else 0.2,
                reasoning_path=[f"Found {len(similar)} similar technologies"],
            )
        finally:
            await self.graph.disconnect()
    
    async def _find_direct(self, source: str, target: str) -> List[Dict]:
        """Find direct relations."""
        relations = []
        
        if self.graph._driver:
            async with self.graph._driver.session() as session:
                result = await session.run("""
                    MATCH (a:Entity)-[r]-(b:Entity)
                    WHERE toLower(a.name) CONTAINS toLower($source)
                      AND toLower(b.name) CONTAINS toLower($target)
                    RETURN a.name as source, type(r) as relation, b.name as target
                """, {"source": source, "target": target})
                
                async for record in result:
                    relations.append({
                        "source": record["source"],
                        "relation": record["relation"],
                        "target": record["target"],
                    })
        
        return relations
    
    async def _find_indirect(self, source: str, target: str) -> List[Dict]:
        """Find indirect relations (1-hop)."""
        relations = []
        
        if self.graph._driver:
            async with self.graph._driver.session() as session:
                result = await session.run("""
                    MATCH (a:Entity)-[r1]-(mid:Entity)-[r2]-(b:Entity)
                    WHERE toLower(a.name) CONTAINS toLower($source)
                      AND toLower(b.name) CONTAINS toLower($target)
                    RETURN a.name as source, mid.name as via,
                           type(r1) as rel1, type(r2) as rel2, b.name as target
                    LIMIT 10
                """, {"source": source, "target": target})
                
                async for record in result:
                    relations.append({
                        "source": record["source"],
                        "via": record["via"],
                        "relation1": record["rel1"],
                        "relation2": record["rel2"],
                        "target": record["target"],
                    })
        
        return relations

