"""
ShopGraph Cypher Safety & Security Validator
============================================
Enforces strict read-only execution, label/relationship allowlists,
and structural boundary checks against untrusted generated Cypher.
"""

import re
from typing import List, Set, Tuple

# Disallowed mutating and administrative keywords
FORBIDDEN_KEYWORDS = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bDETACH\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bCALL\s+dbms\b",
    r"\bCALL\s+apoc\.system\b",
    r"\bLOAD\s+CSV\b",
    r"\bPERIODIC\s+COMMIT\b",
]

# Strict allowlist of permitted procedures (db.index.vector.queryNodes is the only procedure required)
ALLOWED_PROCEDURES: Set[str] = {
    "db.index.vector.queryNodes",
}

# Strict allowlist of permitted Node labels
ALLOWED_NODE_LABELS: Set[str] = {
    "Product",
    "User",
    "Review",
    "Brand",
    "Category",
}

# Strict allowlist of permitted Relationship types
ALLOWED_RELATIONSHIPS: Set[str] = {
    "WROTE",
    "REVIEWS",
    "PURCHASED",
    "BRANDED_BY",
    "BELONGS_TO",
    "SUB_CATEGORY_OF",
}

# Forbidden fabricated relationships from PRD
FORBIDDEN_RELATIONSHIPS: Set[str] = {
    "BOUGHT_TOGETHER",
    "CO_PURCHASED",
    "OWNS",
    "PURCHASED_ON",
    "SIMILAR_TO",
    "CO_REVIEWED",
}


class CypherValidationError(Exception):
    """Raised when Cypher violates read-only or schema safety policies."""
    pass


class CypherValidator:
    """Validates that a Cypher query is 100% read-only, bounds-checked, and uses only approved schema."""

    def validate(self, cypher: str) -> Tuple[bool, List[str]]:
        """
        Validates the given query against all safety rules.
        Returns (is_valid, list_of_violations).
        """
        violations: List[str] = []
        cleaned_cypher = self._strip_comments_and_literals(cypher).strip()

        if not cleaned_cypher:
            return False, ["Query is empty."]

        # 1. Read-only keyword check
        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, cleaned_cypher, re.IGNORECASE):
                violations.append(f"Disallowed mutating or administrative keyword detected matching '{pattern}'.")

        # 2. Must start with read-only clause (MATCH, WITH, OPTIONAL, UNWIND, CALL)
        if not re.match(r"^(?:MATCH|OPTIONAL\s+MATCH|WITH|UNWIND|CALL)\b", cleaned_cypher, re.IGNORECASE):
            violations.append("Query must begin with a read-only clause (MATCH, WITH, OPTIONAL MATCH).")

        # 3. Must contain RETURN clause
        if not re.search(r"\bRETURN\b", cleaned_cypher, re.IGNORECASE):
            violations.append("Query must contain a RETURN clause.")

        # 4. Strict Procedure Allowlist for CALL invocations
        # Enforces that CALL can only invoke explicitly permitted procedures.
        # Arbitrary CALL, apoc.*, dbms.*, file/export, system, or administrative procedures are rejected.
        call_matches = re.finditer(
            r"\bCALL\b(?:\s*\{|\s+[`]?([a-zA-Z0-9_.]+)[`]?)?",
            cleaned_cypher,
            re.IGNORECASE,
        )
        for cm in call_matches:
            proc_target = cm.group(1)
            if not proc_target:
                violations.append(
                    f"Disallowed arbitrary CALL clause or subquery. "
                    f"Only the following procedure is permitted: {sorted(ALLOWED_PROCEDURES)}"
                )
            else:
                proc_clean = proc_target.strip("` ")
                if not any(proc_clean.lower() == p.lower() for p in ALLOWED_PROCEDURES):
                    violations.append(
                        f"Disallowed Cypher procedure call '{proc_clean}'. "
                        f"Only the following procedure is permitted: {sorted(ALLOWED_PROCEDURES)}"
                    )

        # 5. Check Node Labels against Allowlist
        # Matches patterns like (p:Product) or (:Category) or (u:User:Customer)
        label_matches = re.findall(r"\(\s*[a-zA-Z0-9_]*\s*:([a-zA-Z0-9_:]+)\s*\)", cleaned_cypher)
        for group in label_matches:
            labels = group.split(":")
            for label in labels:
                label_clean = label.strip()
                if label_clean and label_clean not in ALLOWED_NODE_LABELS:
                    violations.append(f"Forbidden or unknown Node label: '{label_clean}'. Permitted labels: {sorted(ALLOWED_NODE_LABELS)}")

        # 6. Check Relationship Types against Allowlist & Forbidden List
        # Matches patterns like -[:REL_NAME]-> or -[:REL_NAME*1..2]-
        rel_matches = re.findall(r"-\[\s*[a-zA-Z0-9_]*\s*:([a-zA-Z0-9_]+)(?:[*\s0-9.]*)\s*\]-", cleaned_cypher)
        for rel in rel_matches:
            rel_clean = rel.strip()
            if rel_clean in FORBIDDEN_RELATIONSHIPS:
                violations.append(
                    f"Strictly forbidden relationship type '{rel_clean}'. "
                    f"Combinatorial or non-observed edges must never be queried directly."
                )
            elif rel_clean not in ALLOWED_RELATIONSHIPS:
                violations.append(
                    f"Unknown or unapproved relationship type '{rel_clean}'. "
                    f"Approved schema relationships: {sorted(ALLOWED_RELATIONSHIPS)}"
                )

        # 7. Reject unconstrained all-nodes scan MATCH (n) RETURN n
        if re.search(r"MATCH\s*\(\s*[a-zA-Z0-9_]*\s*\)\s*RETURN", cleaned_cypher, re.IGNORECASE):
            violations.append("Unrestricted full-graph scan MATCH (n) RETURN ... is prohibited.")

        is_valid = len(violations) == 0
        return is_valid, violations

    def assert_safe(self, cypher: str):
        """Throws CypherValidationError if the query violates any rule."""
        is_valid, violations = self.validate(cypher)
        if not is_valid:
            msg = "Cypher safety validation failed:\n" + "\n".join(f"- {v}" for v in violations)
            raise CypherValidationError(msg)

    def _strip_comments_and_literals(self, text: str) -> str:
        """Strips single/multi-line comments and string literals to prevent regex false positives."""
        # Strip // comments
        no_single = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
        # Strip /* ... */ comments
        no_multi = re.sub(r"/\*.*?\*/", "", no_single, flags=re.DOTALL)
        # Strip string literals '...' or "..."
        no_strings = re.sub(r"'[^']*'", "''", no_multi)
        no_strings = re.sub(r'"[^"]*"', '""', no_strings)
        return no_strings


# Global singleton
cypher_validator = CypherValidator()
