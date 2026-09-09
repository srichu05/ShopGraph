"""Neo4j Database module."""
from app.db.neo4j.connection import neo4j_client, Neo4jClient

__all__ = ["neo4j_client", "Neo4jClient"]
