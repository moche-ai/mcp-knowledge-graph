"""Knowledge graph data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid


class EntityType(str, Enum):
    """Entity types in the knowledge graph."""
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    FRAMEWORK = "framework"
    TOOL = "tool"
    LANGUAGE = "language"
    PATTERN = "pattern"
    BEST_PRACTICE = "best_practice"
    ORGANIZATION = "organization"
    PERSON = "person"
    DOCUMENT = "document"


class RelationType(str, Enum):
    """Relation types between entities."""
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    ALTERNATIVE_TO = "alternative_to"
    INTEGRATES_WITH = "integrates_with"
    PART_OF = "part_of"
    EXTENDS = "extends"
    USES = "uses"
    CREATED_BY = "created_by"
    REFERENCES = "references"


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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


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

