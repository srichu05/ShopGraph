"""
Neo4j Database Driver and Session Lifecycle Management
======================================================
Provides thread-safe driver access, connection health checks,
query execution helpers with timeout controls, and structured error reporting.
"""

import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, ConfigurationError

from app.config import settings

logger = logging.getLogger("shopgraph.db")


class Neo4jClient:
    """Thread-safe Neo4j client with lifecycle management and health monitoring."""

    def __init__(self):
        self._driver: Optional[Driver] = None
        self._is_connected: bool = False

    def connect(self) -> bool:
        """Attempt to establish driver connection to Neo4j."""
        if self._driver is not None:
            return self._is_connected

        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_lifetime=settings.NEO4J_MAX_CONNECTION_LIFETIME,
                max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
            )
            self._driver.verify_connectivity()
            self._is_connected = True
            logger.info("Connected to Neo4j at %s", settings.NEO4J_URI)
            return True
        except (ServiceUnavailable, ConnectionRefusedError, OSError) as e:
            logger.warning("Neo4j is currently unreachable at %s: %s", settings.NEO4J_URI, e)
            self._is_connected = False
            return False
        except AuthError as e:
            logger.error("Neo4j authentication failed: %s", e)
            self._is_connected = False
            return False
        except Exception as e:
            logger.error("Unexpected error connecting to Neo4j: %s", e)
            self._is_connected = False
            return False

    def is_available(self) -> bool:
        """Quickly check if Neo4j is reachable without throwing unhandled exceptions."""
        if not self._driver or not self._is_connected:
            return self.connect()
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            self._is_connected = False
            return False

    def close(self):
        """Close driver connections on shutdown."""
        if self._driver:
            try:
                self._driver.close()
            except Exception as e:
                logger.warning("Error closing Neo4j driver: %s", e)
            self._driver = None
            self._is_connected = False

    def execute_read(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a read query with parameterized inputs and timeout safeguards.
        Raises RuntimeError if Neo4j is unavailable.
        """
        if not self.is_available():
            raise RuntimeError(
                f"Neo4j database is unavailable at {settings.NEO4J_URI}. "
                "Ensure Neo4j is running or configure remote Aura credentials in .env."
            )

        db = database or settings.NEO4J_DATABASE
        params = parameters or {}
        timeout_sec = float(timeout_ms or settings.NEO4J_QUERY_TIMEOUT_MS) / 1000.0

        try:
            with self._driver.session(database=db) as session:
                result = session.run(query, params, timeout=timeout_sec)
                return result.data()
        except Exception as e:
            logger.error("Neo4j query execution failed: %s | Query: %s", e, query)
            raise


# Global singleton
neo4j_client = Neo4jClient()
