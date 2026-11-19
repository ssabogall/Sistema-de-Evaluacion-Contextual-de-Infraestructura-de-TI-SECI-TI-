"""RNF-02: el mismo caso produce siempre la misma recomendacion.

Umbral: 100 % de coincidencia en 5 o mas ejecuciones del mismo caso. Se verifica en
tres niveles: misma entrada reutilizada, entradas reconstruidas desde cero y procesos
de Python distintos con semillas de hash diferentes (el orden de sets y dicts de str
depende de esa semilla, asi que es la fuente de no determinismo mas probable).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.decision_engine.engine import evaluate
from tests.curated_engine_cases import CURATED_ENGINE_CASES
from tests.test_engine_accuracy import build_inputs

REPETITIONS = 10
HASH_SEEDS = ("0", "1", "12345")
BACKEND_ROOT = Path(__file__).resolve().parents[1]

_SNAPSHOT_SCRIPT = """
import json
from app.decision_engine.engine import evaluate
from tests.curated_engine_cases import CURATED_ENGINE_CASES
from tests.test_engine_accuracy import build_inputs

print(json.dumps(
    {case.case_id: evaluate(*build_inputs(case)).model_dump(mode="json")
     for case in CURATED_ENGINE_CASES},
    sort_keys=True,
))
"""


def _snapshot_in_new_process(hash_seed: str) -> dict:
    env = {
        **os.environ,
        "PYTHONHASHSEED": hash_seed,
        "PYTHONPATH": os.pathsep.join(
            filter(None, [str(BACKEND_ROOT), os.environ.get("PYTHONPATH")])
        ),
    }
    completed = subprocess.run(
        [sys.executable, "-c", _SNAPSHOT_SCRIPT],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize("case", CURATED_ENGINE_CASES, ids=lambda case: case.case_id)
def test_same_inputs_give_identical_recommendation(case) -> None:
    requirements, ranking = build_inputs(case)
    first = evaluate(requirements, ranking).model_dump(mode="json")

    for _ in range(REPETITIONS):
        assert evaluate(requirements, ranking).model_dump(mode="json") == first


@pytest.mark.parametrize("case", CURATED_ENGINE_CASES, ids=lambda case: case.case_id)
def test_rebuilt_inputs_give_identical_recommendation(case) -> None:
    first = evaluate(*build_inputs(case)).model_dump(mode="json")

    for _ in range(REPETITIONS):
        assert evaluate(*build_inputs(case)).model_dump(mode="json") == first


def test_recommendations_do_not_depend_on_the_python_hash_seed() -> None:
    snapshots = [_snapshot_in_new_process(seed) for seed in HASH_SEEDS]

    assert len(snapshots[0]) == len(CURATED_ENGINE_CASES)
    for seed, snapshot in zip(HASH_SEEDS[1:], snapshots[1:], strict=True):
        assert snapshot == snapshots[0], f"PYTHONHASHSEED={seed} cambio el resultado"
