"""Knowledge graph data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid


class EntityType(str, Enum):
    """Entity types in the knowledge graph."""
    # Technology
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    FRAMEWORK = "framework"
    MODEL = "model"
    SERVICE = "service"
    TOOL = "tool"
    LANGUAGE = "language"
    PATTERN = "pattern"
    BEST_PRACTICE = "best_practice"
    PROJECT = "project"
    
    # People & Organizations
    ORGANIZATION = "organization"
    PERSON = "person"
    
    # Content
    DOCUMENT = "document"
    NEWS = "news"
    
    # Finance/Assets
    CRYPTOCURRENCY = "cryptocurrency"
    STOCK = "stock"
    ASSET = "asset"


class RelationType(str, Enum):
    """Relation types between entities."""
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    ALTERNATIVE_TO = "alternative_to"
    SIMILAR_TO = "similar_to"
    INTEGRATES_WITH = "integrates_with"
    PART_OF = "part_of"
    EXTENDS = "extends"
    USES = "uses"
    CREATED_BY = "created_by"
    REFERENCES = "references"
    COMPETES_WITH = "competes_with"


class TrustLevel(str, Enum):
    """Trust levels for knowledge verification."""
    VERIFIED = "verified"      # 0.9-1.0
    HIGH = "high"              # 0.7-0.9
    MEDIUM = "medium"          # 0.5-0.7
    LOW = "low"                # 0.3-0.5
    UNVERIFIED = "unverified"  # 0.0-0.3


@dataclass
class Entity:
    """An entity in the knowledge graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    trust_score: float = 0.5
    trust_level: TrustLevel = TrustLevel.MEDIUM
    source_url: str = ""
    source_count: int = 1
    service_id: str = "global"
    user_id: str = "shared"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "tags": self.tags,
            "trust_score": self.trust_score,
            "trust_level": self.trust_level.value,
            "source_url": self.source_url,
            "source_count": self.source_count,
            "service_id": self.service_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Create from dictionary."""
        entity_type = data.get("entity_type", "concept")
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type)
            except ValueError:
                entity_type = EntityType.CONCEPT
        
        trust_level = data.get("trust_level", "medium")
        if isinstance(trust_level, str):
            try:
                trust_level = TrustLevel(trust_level)
            except ValueError:
                trust_level = TrustLevel.MEDIUM
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            entity_type=entity_type,
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            tags=data.get("tags", []),
            trust_score=data.get("trust_score", 0.5),
            trust_level=trust_level,
            source_url=data.get("source_url", ""),
            source_count=data.get("source_count", 1),
            service_id=data.get("service_id", "global"),
            user_id=data.get("user_id", "shared"),
        )


@dataclass
class Relation:
    """A relation between two entities."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    trust_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "properties": self.properties,
            "weight": self.weight,
            "trust_score": self.trust_score,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        """Create from dictionary."""
        relation_type = data.get("relation_type", "related_to")
        if isinstance(relation_type, str):
            try:
                relation_type = RelationType(relation_type)
            except ValueError:
                relation_type = RelationType.RELATED_TO
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relation_type=relation_type,
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            trust_score=data.get("trust_score", 0.5),
        )
