"""Configuration for MCP Knowledge Graph Server."""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Server configuration."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = int(os.getenv("MCP_PORT", "8780"))
    
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    
    # Knowledge Graph
    default_service_id: str = "global"
    min_trust_score: float = float(os.getenv("MIN_TRUST_SCORE", "0.7"))
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()


config = Config.from_env()

