"""
ShopGraph Cypher Sanitizer & Parameterizer
=========================================
Ensures query parameterization, enforces strict LIMIT bounds,
and defends against parameter-level injection.
"""

import re
from typing import Any, Dict, Optional, Tuple
from app.config import settings


class CypherSanitizer:
    """Enforces query boundaries, limits, and parameter mapping."""

    @staticmethod
    def enforce_limit(cypher: str, requested_limit: Optional[int] = None) -> Tuple[str, int]:
        """
        Ensures the query has a bounded LIMIT clause.
        Clamps any existing literal LIMIT to settings.NEO4J_MAX_RESULTS.
        """
        max_allowed = settings.NEO4J_MAX_RESULTS
        target_limit = min(requested_limit or settings.DEFAULT_RETRIEVAL_LIMIT, max_allowed)

        # Check for existing LIMIT clause at the end
        m_limit = re.search(r"\bLIMIT\s+(\d+)\s*;?$", cypher, re.IGNORECASE)
        if m_limit:
            existing_limit = int(m_limit.group(1))
            if existing_limit > max_allowed:
                # Clamp it
                cleaned = re.sub(r"\bLIMIT\s+\d+\s*;?$", f"LIMIT {max_allowed}", cypher, flags=re.IGNORECASE)
                return cleaned, max_allowed
            return cypher, existing_limit

        # If LIMIT uses parameter like LIMIT $limit
        if re.search(r"\bLIMIT\s+\$[a-zA-Z0-9_]+\s*;?$", cypher, re.IGNORECASE):
            return cypher, target_limit

        # No LIMIT clause found -> append parameterized limit
        stripped = cypher.rstrip("; \t\n")
        bounded_cypher = f"{stripped}\nLIMIT $limit"
        return bounded_cypher, target_limit

    @staticmethod
    def build_safe_params(raw_params: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Validates and types all parameter dictionary values."""
        params: Dict[str, Any] = {}
        if raw_params:
            for k, v in raw_params.items():
                # Sanitize parameter keys to alphanumeric/underscore
                safe_key = re.sub(r"[^a-zA-Z0-9_]", "", k)
                if not safe_key:
                    continue

                # Type-check values
                if isinstance(v, (int, float, bool, str)) or v is None:
                    params[safe_key] = v
                elif isinstance(v, list):
                    # Lists of primitives
                    params[safe_key] = [item for item in v if isinstance(item, (int, float, bool, str))]
                else:
                    params[safe_key] = str(v)

        # Guarantee $limit parameter
        target_limit = min(limit or settings.DEFAULT_RETRIEVAL_LIMIT, settings.NEO4J_MAX_RESULTS)
        params["limit"] = target_limit
        return params


cypher_sanitizer = CypherSanitizer()
