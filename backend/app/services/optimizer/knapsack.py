"""PuLP 0/1 knapsack solver for plan optimization (ADR-004)."""

from __future__ import annotations

import time
import uuid
from typing import Any

from pulp import LpMaximize, LpProblem, LpStatus, LpVariable, PULP_CBC_CMD, lpSum, value


def solve_knapsack(
    perks: list[dict[str, Any]],
    budget_cents: int,
    *,
    timeout_seconds: int = 5,
) -> dict[str, Any]:
    """Solve 0/1 knapsack: weight=employee_price_cents, value=recommendation_score.

    Returns status, approved/excluded ids, totals, and solver_time_ms.
    """

    start = time.time()

    if not perks:
        return {
            "status": "infeasible",
            "approved_ids": [],
            "excluded_ids": [],
            "total_cost_cents": 0,
            "total_score": 0.0,
            "solver_time_ms": 0,
        }

    prob = LpProblem("perk_knapsack", LpMaximize)
    x = {p["id"]: LpVariable(f"x_{p['id']}", cat="Binary") for p in perks}

    prob += lpSum(p["score"] * x[p["id"]] for p in perks)
    prob += lpSum(p["price_cents"] * x[p["id"]] for p in perks) <= budget_cents

    solver = PULP_CBC_CMD(msg=0, timeLimit=timeout_seconds)
    prob.solve(solver)

    solver_ms = int((time.time() - start) * 1000)
    pulp_status = LpStatus[prob.status]
    status = pulp_status.lower() if pulp_status in ("Optimal", "Feasible") else "infeasible"

    approved_ids: list[uuid.UUID] = [
        p["id"]
        for p in perks
        if value(x[p["id"]]) is not None and value(x[p["id"]]) > 0.5
    ]
    excluded_ids = [p["id"] for p in perks if p["id"] not in approved_ids]

    return {
        "status": status,
        "approved_ids": approved_ids,
        "excluded_ids": excluded_ids,
        "total_cost_cents": sum(p["price_cents"] for p in perks if p["id"] in approved_ids),
        "total_score": sum(p["score"] for p in perks if p["id"] in approved_ids),
        "solver_time_ms": solver_ms,
    }
