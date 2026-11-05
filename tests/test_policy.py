import math

import pytest

from shunt import ROUTES, route


def decide(p=(0.8, 0.1, 0.1), *, files=1, lines=20, attempts=0, task="format code", core=False):
    return route(task, list(p), files, lines, attempts, core)


def test_routes_and_stable_tie():
    assert ROUTES == ("T1", "T2", "T3")
    result = decide((0.4, 0.4, 0.2))
    assert result["route"] == ROUTES[1]  # stable Tier 1 winner, then ambiguity promotion
    assert result["semantic_margin"] == pytest.approx(0)


@pytest.mark.parametrize(("lines", "expected"), [(49, 1), (50, 2)])
def test_ast_boundary(lines, expected):
    assert decide(lines=lines)["overrides"]["structural_floor"] == expected


@pytest.mark.parametrize(("files", "expected"), [(8, 2), (9, 3)])
def test_file_boundary(files, expected):
    assert decide(files=files, lines=60)["overrides"]["structural_floor"] == expected


@pytest.mark.parametrize(("attempts", "expected"), [(0, 1), (1, 2), (2, 3)])
def test_retry_floor(attempts, expected):
    result = decide(attempts=attempts)
    assert result["overrides"]["structural_floor"] == expected
    assert result["overrides"]["circuit_breaker"] is (attempts >= 2)


def test_exact_margin_boundary_is_not_ambiguous():
    result = decide((0.575, 0.425, 0), files=1, lines=49)
    assert math.isclose(result["semantic_margin"], 0.15)
    assert result["overrides"]["ambiguity_bump"] is False
    assert result["route"] == ROUTES[0]


def test_unknown_scope_floors_to_tier3():
    result = decide(files=None, lines=20)
    assert result["overrides"]["unknown_scope"] is True
    assert result["overrides"]["structural_floor"] == 3
    assert result["route"] == ROUTES[2]


@pytest.mark.parametrize("bad", [[0, 0, 0], [0.4, 0.4, 0.4], [float("nan"), 0, 1], [float("inf"), 0, 0], [-0.1, 0.5, 0.6], [True, 0, 0]])
def test_rejects_malformed_probabilities(bad):
    with pytest.raises(ValueError):
        decide(tuple(bad))


@pytest.mark.parametrize("kwargs", [
    {"files": True}, {"files": -1}, {"lines": False}, {"lines": 2.5},
    {"attempts": True}, {"attempts": -1}, {"core": 1},
])
def test_rejects_bool_or_invalid_counts(kwargs):
    with pytest.raises(ValueError):
        decide(**kwargs)


@pytest.mark.parametrize(("task", "risk"), [
    ("async worker", True), ("mutex handling", True), ("check lock", True),
    ("atomic update", True), ("race condition", True), ("segfault", True),
    ("deadlock", True), ("OOM recovery", True), ("migration", True),
    ("cryptography setup", True), ("auth_handler", True), ("clock formatting", False),
    ("authorization page", False),
])
def test_lexical_risk_tokens(task, risk):
    result = decide(task=task)
    assert result["overrides"]["lexical_risk"] is risk
    if risk:
        assert result["route"] == ROUTES[2]


def test_core_interface_is_tier3():
    assert decide(core=True)["overrides"]["structural_floor"] == 3


def test_task_required():
    with pytest.raises(ValueError):
        decide(task="  ")
