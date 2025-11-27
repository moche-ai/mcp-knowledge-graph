"""Neo4j Knowledge Graph operations."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, ClassVar

from neo4j import AsyncGraphDatabase

from ..config import config
from .models import Entity, Relation, EntityType, RelationType


class KnowledgeGraph:
    """
    Neo4j-based knowledge graph for storing and querying verified knowledge.
    
    Features:
    - Entity and relation management
    - Trust score tracking
    - Relationship traversal
    - Pattern matching queries
    - Shared driver pattern (singleton)
    """
    
    # 클래스 레벨 공유 드라이버
    _shared_driver: ClassVar[Optional[Any]] = None
    _initialized: ClassVar[bool] = False
    
    def __init__(self, use_shared: bool = True):
        """
        Initialize KnowledgeGraph.
        
        Args:
            use_shared: 공유 드라이버 사용 여부 (기본값 True)
        """
        self._use_shared = use_shared
        self._local_driver = None
    
    @classmethod
    async def get_shared_driver(cls):
        """Get or create shared Neo4j driver."""
        if cls._shared_driver is None and config.neo4j_password:
            try:
                cls._shared_driver = AsyncGraphDatabase.driver(
                    config.neo4j_uri,
                    auth=(config.neo4j_user, config.neo4j_password),
                )
                cls._initialized = True
            except Exception as e:
                print(f"Neo4j connection error: {e}")
                return None
        return cls._shared_driver
    
    @classmethod
    async def close_shared_driver(cls):
        """Close shared driver."""
        if cls._shared_driver:
            await cls._shared_driver.close()
            cls._shared_driver = None
            cls._initialized = False
    
    @property
    def _driver(self):
        """Get driver (shared or local)."""
        if self._use_shared:
            return self._shared_driver
        return self._local_driver
    
    async def connect(self):
        """Connect to Neo4j database."""
        if self._use_shared:
            await self.get_shared_driver()
        elif not self._local_driver and config.neo4j_password:
            self._local_driver = AsyncGraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_user, config.neo4j_password),
            )
    
    async def disconnect(self):
        """Disconnect from Neo4j database."""
        # 공유 드라이버는 여기서 닫지 않음
        if not self._use_shared and self._local_driver:
            await self._local_driver.close()
            self._local_driver = None
    
    async def run_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        await self.connect()
        
        results = []
        driver = self._driver
        
        if not driver:
            return results
        
        try:
            async with driver.session() as session:
                result = await session.run(query, params or {})
                async for record in result:
                    results.append(dict(record))
        except Exception as e:
            print(f"Query error: {e}")
        
        return results
    
    async def get_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an entity by name."""
        await self.connect()
        
        driver = self._driver
        if not driver:
            return None
        
        async with driver.session() as session:
            result = await session.run("""
                MATCH (e:Entity {name: $name})
                RETURN e.name as name, e.entity_type as type, 
                       e.description as description, e.trust_score as trust,
                       e.properties as properties
            """, {"name": name})
            
            record = await result.single()
            if record:
                props = self._parse_properties(record["properties"])
                return {
                    "name": record["name"],
                    "type": record["type"],
                    "description": record["description"],
                    "trust_score": record["trust"],
                    "properties": props,
                }
        
        return None
    
    async def search_entities(
        self, 
        query: str, 
        min_trust: float = 0.5,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search entities by keyword."""
        await self.connect()
        
        results = []
        driver = self._driver
        
        if not driver:
            return results
        
        async with driver.session() as session:
            result = await session.run("""
                MATCH (e:Entity)
                WHERE e.trust_score >= $min_trust
                  AND (toLower(e.name) CONTAINS toLower($query)
                       OR toLower(e.description) CONTAINS toLower($query))
                RETURN e.name as name, e.entity_type as type,
                       e.description as description, e.trust_score as trust,
                       e.properties as properties
                ORDER BY e.trust_score DESC
                LIMIT $limit
            """, {"query": query, "min_trust": min_trust, "limit": limit})
            
            async for record in result:
                props = self._parse_properties(record["properties"])
                results.append({
                    "name": record["name"],
                    "type": record["type"],
                    "description": record["description"],
                    "trust_score": record["trust"],
                    "stars": props.get("stars", 0),
                    "installation": props.get("installation", ""),
                })
        
        return results
    
    async def get_relations(self, name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all relations for an entity."""
        await self.connect()
        
        relations = {
            "depends_on": [],
            "integrates_with": [],
            "alternative_to": [],
            "part_of": [],
            "other": [],
        }
        
        driver = self._driver
        if not driver:
            return relations
        
        async with driver.session() as session:
            # Outgoing relations
            result = await session.run("""
                MATCH (e:Entity {name: $name})-[r]->(target:Entity)
                RETURN type(r) as relation, target.name as target_name,
                       target.description as description, target.trust_score as trust
            """, {"name": name})
            
            async for record in result:
                rel_type = record["relation"].lower()
                rel_data = {
                    "name": record["target_name"],
                    "description": record["description"],
                    "trust_score": record["trust"],
                    "direction": "outgoing",
                }
                
                if rel_type in relations:
                    relations[rel_type].append(rel_data)
                else:
                    relations["other"].append(rel_data)
            
            # Incoming relations
            result = await session.run("""
                MATCH (source:Entity)-[r]->(e:Entity {name: $name})
                RETURN type(r) as relation, source.name as source_name,
                       source.description as description, source.trust_score as trust
            """, {"name": name})
            
            async for record in result:
                rel_type = record["relation"].lower()
                rel_data = {
                    "name": record["source_name"],
                    "description": record["description"],
                    "trust_score": record["trust"],
                    "direction": "incoming",
                }
                
                if rel_type in relations:
                    relations[rel_type].append(rel_data)
                else:
                    relations["other"].append(rel_data)
        
        return relations
    
    async def get_dependency_chain(
        self, 
        name: str, 
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Get recursive dependency chain."""
        await self.connect()
        
        chain = []
        driver = self._driver
        
        if not driver:
            return chain
        
        async with driver.session() as session:
            query = f"""
                MATCH path = (e:Entity {{name: $name}})-[:depends_on*1..{max_depth}]->(dep:Entity)
                RETURN dep.name as name, dep.description as description,
                       length(path) as depth
                ORDER BY depth
            """
            result = await session.run(query, {"name": name})
            
            async for record in result:
                chain.append({
                    "name": record["name"],
                    "description": record["description"],
                    "depth": record["depth"],
                })
        
        return chain
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        await self.connect()
        
        stats = {
            "total_entities": 0,
            "total_relations": 0,
            "average_trust_score": 0.0,
            "entity_types": {},
        }
        
        driver = self._driver
        if not driver:
            return stats
        
        async with driver.session() as session:
            # Entity count
            result = await session.run("MATCH (n:Entity) RETURN count(n) as count")
            record = await result.single()
            stats["total_entities"] = record["count"] if record else 0
            
            # Relation count
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            stats["total_relations"] = record["count"] if record else 0
            
            # Average trust
            result = await session.run("MATCH (n:Entity) RETURN avg(n.trust_score) as avg")
            record = await result.single()
            stats["average_trust_score"] = float(record["avg"]) if record and record["avg"] else 0.0
            
            # Entity types
            result = await session.run("""
                MATCH (n:Entity)
                RETURN n.entity_type as type, count(n) as count
                ORDER BY count DESC
            """)
            async for record in result:
                stats["entity_types"][record["type"] or "unknown"] = record["count"]
        
        return stats
    
    @staticmethod
    def _parse_properties(properties_data) -> Dict[str, Any]:
        """Parse properties from Neo4j record."""
        if not properties_data:
            return {}
        
        try:
            if isinstance(properties_data, str):
                return json.loads(properties_data)
            elif isinstance(properties_data, dict):
                return properties_data
        except (json.JSONDecodeError, TypeError):
            pass
        
        return {}
