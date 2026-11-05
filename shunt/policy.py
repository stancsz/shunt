"""Pure deterministic routing policy; model probabilities are supplied by callers."""

import math
import re
from typing import Any

ROUTES = ("T1", "T2", "T3")
_RISK_TOKENS = frozenset(
    {"async", "mutex", "lock", "atomic", "race", "segfault", "deadlock", "oom", "migration", "cryptography", "auth"}
)
_AMBIGUITY_MARGIN = 0.15
_MARGIN_TOLERANCE = 1e-12


def _count(value: int | None, name: str) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError(f"{name} must be a nonnegative integer or None")


def route(
    task: str,
    probabilities: list[float],
    file_count: int | None,
    ast_lines: int | None,
    attempt_count: int = 0,
    core_interface: bool = False,
) -> dict[str, Any]:
    """Choose a route from normalized semantic probabilities and explicit scope evidence."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a nonempty string")
    if not isinstance(probabilities, list) or len(probabilities) != len(ROUTES):
        raise ValueError("probabilities must be a list of exactly three numbers")
    values: list[float] = []
    for probability in probabilities:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise ValueError("probabilities must be finite nonnegative numbers")
        value = float(probability)
        if not math.isfinite(value) or value < 0:
            raise ValueError("probabilities must be finite nonnegative numbers")
        values.append(value)
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("probabilities must sum to one")
    _count(file_count, "file_count")
    _count(ast_lines, "ast_lines")
    if isinstance(attempt_count, bool) or not isinstance(attempt_count, int) or attempt_count < 0:
        raise ValueError("attempt_count must be a nonnegative integer")
    if not isinstance(core_interface, bool):
        raise ValueError("core_interface must be a boolean")

    # max() retains the first index on ties, making argmax stable in ROUTES order.
    winner = max(range(3), key=values.__getitem__)
    ordered = sorted(values, reverse=True)
    margin = ordered[0] - ordered[1]
    ambiguity = margin < _AMBIGUITY_MARGIN and not math.isclose(
        margin, _AMBIGUITY_MARGIN, rel_tol=0.0, abs_tol=_MARGIN_TOLERANCE
    )

    tokens = re.findall(r"[a-z0-9]+", task.lower())
    lexical_risk = bool(_RISK_TOKENS.intersection(tokens))
    unknown_scope = file_count is None or ast_lines is None
    blast_radius = file_count is not None and file_count > 8
    circuit_breaker = attempt_count >= 2

    # Tier 1 is eligible only with complete small scope and no prior failure.
    tier1_scope = file_count == 1 and ast_lines is not None and ast_lines < 50 and attempt_count == 0
    structural_floor = 1 if tier1_scope else 2
    if unknown_scope or blast_radius or core_interface or circuit_breaker or lexical_risk:
        structural_floor = 3

    semantic_tier = winner + 1
    promoted = min(3, semantic_tier + 1) if ambiguity else semantic_tier
    final_tier = max(structural_floor, promoted)
    flags = {
        "lexical_risk": lexical_risk,
        "ambiguity_bump": ambiguity,
        "circuit_breaker": circuit_breaker,
        "blast_radius": blast_radius,
        "core_interface": core_interface,
        "unknown_scope": unknown_scope,
        "structural_floor": structural_floor,
    }
    return {
        "route": ROUTES[final_tier - 1],
        "probabilities": dict(zip(ROUTES, values)),
        "semantic_margin": margin,
        "ast_file_count": file_count,
        "overrides": flags,
    }
