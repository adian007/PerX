"""Nightly ALS retrain script — reads fixture interactions and outputs CF scores."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "interactions.json"
OUTPUT_PATH = Path(__file__).parent / "output" / "cf_scores_by_employee.json"


def load_fixture(path: Path = FIXTURE_PATH) -> dict:
    """Load interaction fixture from JSON."""

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_interaction_matrix(fixture: dict) -> sp.csr_matrix:
    """Build a sparse employee x perk interaction matrix from events."""

    num_employees = len(fixture["employees"])
    num_perks = len(fixture["perks"])
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for event in fixture["events"]:
        rows.append(int(event["employee_idx"]))
        cols.append(int(event["perk_idx"]))
        data.append(float(event["weight"]))

    matrix = sp.csr_matrix(
        (data, (rows, cols)),
        shape=(num_employees, num_perks),
        dtype=np.float32,
    )
    return matrix


def train_als(matrix: sp.csr_matrix) -> AlternatingLeastSquares:
    """Train an ALS model on the interaction matrix."""

    model = AlternatingLeastSquares(
        factors=50,
        iterations=15,
        regularization=0.01,
        random_state=42,
    )
    model.fit(matrix)
    return model


def score_all_employees(
    model: AlternatingLeastSquares,
    matrix: sp.csr_matrix,
    fixture: dict,
) -> dict[str, dict[str, float]]:
    """Return CF scores keyed by employee id and perk id."""

    scores_by_employee: dict[str, dict[str, float]] = {}
    employee_ids = [employee["id"] for employee in fixture["employees"]]
    perk_ids = [perk["id"] for perk in fixture["perks"]]

    for employee_idx, employee_id in enumerate(employee_ids):
        perk_scores, perk_indices = model.recommend(
            employee_idx,
            matrix[employee_idx],
            N=len(perk_ids),
            filter_already_liked_items=False,
        )
        scores_by_employee[employee_id] = {
            perk_ids[int(perk_indices[i])]: float(perk_scores[i])
            for i in range(len(perk_indices))
        }

    return scores_by_employee


def main() -> None:
    """Train ALS on fixture data and write CF scores to output JSON."""

    fixture = load_fixture()
    matrix = build_interaction_matrix(fixture)
    model = train_als(matrix)
    scores = score_all_employees(model, matrix, fixture)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)

    print(json.dumps(scores, indent=2))
    print(f"\nWrote CF scores to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
