"""RNF-03: el motor evalua un caso rapido y sin depender de llamadas externas.

El requisito pide un tiempo "del orden de segundos, no minutos". Se fija como techo
MAX_SECONDS_PER_EVALUATION sobre el percentil 95; el valor medido real es varios
ordenes de magnitud menor y se imprime con `pytest tests/test_engine_performance.py -s`.
"""

import socket
import statistics
import time

import pytest

from app.decision_engine.engine import evaluate
from tests.curated_engine_cases import CURATED_ENGINE_CASES
from tests.test_engine_accuracy import build_inputs

MAX_SECONDS_PER_EVALUATION = 1.0
REPETITIONS_PER_CASE = 20
WARMUP_RUNS = 5


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


def test_engine_p95_evaluation_time_is_within_rnf_03() -> None:
    inputs = [build_inputs(case) for case in CURATED_ENGINE_CASES]
    for _ in range(WARMUP_RUNS):
        evaluate(*inputs[0])

    samples = []
    for case_inputs in inputs:
        for _ in range(REPETITIONS_PER_CASE):
            start = time.perf_counter()
            evaluate(*case_inputs)
            samples.append(time.perf_counter() - start)

    p50 = statistics.median(samples)
    p95 = _percentile(samples, 0.95)
    print(
        f"\nRNF-03: {len(samples)} evaluaciones | p50 = {p50 * 1000:.3f} ms | "
        f"p95 = {p95 * 1000:.3f} ms | max = {max(samples) * 1000:.3f} ms"
    )
    assert p95 < MAX_SECONDS_PER_EVALUATION


def test_engine_does_not_open_network_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    """El motor es local: si intentara abrir un socket, la prueba falla."""

    def _blocked(*_args, **_kwargs):
        raise AssertionError("El motor de decision intento abrir una conexion de red")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)

    for case in CURATED_ENGINE_CASES:
        evaluate(*build_inputs(case))
