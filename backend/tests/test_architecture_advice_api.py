import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, current_thread
from unittest.mock import Mock

import pytest

from app.ai.architecture_advisor import ArchitectureAdvisor
from app.ai.base import AIConfigurationError, AIProviderError, AIResponseValidationError
from app.config import Settings
from app.decision_engine.engine import evaluate
from app.persistence.repository import CaseStorageError
from app.persistence.sqlite_repository import SqliteCaseRepository
from app.schemas.architecture_advice import AdviceInput, ArchitectureAdvice
from app.schemas.business_case import (
    BusinessCaseConfirmationRequest,
    ConfirmedBusinessCase,
)
from app.services.architecture_advice_service import ArchitectureAdviceService
from tests.helpers import analysis_payload, requirement

BUSINESS_CASE = "La tienda procesa pedidos y requiere continuidad para no perder ventas."
CURRENT_ARCHITECTURE = "Monolito con PostgreSQL en un servidor; respaldo diario sin replicas."
PRIVATE_DETAIL = "fake-private-key-and-sqlite-path-never-expose"


def _advice(summary: str = "Informe inicial", assessment: str | None = None) -> ArchitectureAdvice:
    return ArchitectureAdvice.model_validate(
        {
            "summary": summary,
            "current_architecture_assessment": assessment,
            "recommendations": [
                {
                    "title": "Verificar restauracion de respaldos",
                    "category": "reliability",
                    "priority": "high",
                    "effort": "low",
                    "recommendation": "Ensayar restauracion en un entorno aislado.",
                    "rationale": "Los pedidos necesitan continuidad.",
                    "expected_benefit": "Conocer el tiempo de recuperacion.",
                    "tradeoffs": "Requiere tiempo del equipo y almacenamiento temporal.",
                    "evidence": ["no perder ventas"],
                }
            ],
            "alternatives": [
                {
                    "name": "Base de datos administrada",
                    "description": "Evaluar respaldo y recuperacion administrados.",
                    "suitable_when": "El equipo necesita reducir tareas de operacion.",
                    "tradeoffs": "Tiene un costo mensual que debe validarse.",
                    "migration_steps": ["Probar restauracion y compatibilidad con una copia."],
                }
            ],
            "next_steps": ["Acordar el tiempo de recuperacion con el negocio."],
            "assumptions": ["El equipo puede usar un entorno de pruebas."],
            "open_questions": ["Cuanto tiempo puede tardar la recuperacion?"],
        }
    )


class FakeAdvisor(ArchitectureAdvisor):
    def __init__(self) -> None:
        self.calls: list[AdviceInput] = []
        self.content: ArchitectureAdvice | None = None
        self.error: Exception | None = None

    def recommend(self, payload: AdviceInput) -> ArchitectureAdvice:
        self.calls.append(payload.model_copy(deep=True))
        if self.error is not None:
            raise self.error
        if self.content is not None:
            return self.content.model_copy(deep=True)
        assessment = (
            "El servidor unico requiere validar la recuperacion ante fallos."
            if payload.confirmed.project_context.scenario == "existing"
            else None
        )
        return _advice(assessment=assessment)


def _request(scenario: str = "new") -> dict:
    payload = analysis_payload(
        BUSINESS_CASE,
        service_interruption_tolerance=requirement("low", "detected", ["no perder ventas"]),
        available_budget=requirement("low", "detected", ["presupuesto limitado"]),
    )
    context = {"scenario": scenario, "current_architecture": None}
    if scenario == "existing":
        context["current_architecture"] = CURRENT_ARCHITECTURE
    return {
        "business_case": BUSINESS_CASE,
        "project_context": context,
        "requirements": payload["requirements"],
        "priority_ranking": {
            "never_stop_working": 1,
            "protect_information": 2,
            "fast_under_load": 3,
            "lowest_cost": 4,
        },
    }


def _create_case(client, scenario: str = "new") -> dict:
    response = client.post("/api/cases", json=_request(scenario))
    assert response.status_code == 201, response.text
    return response.json()


def _assert_case_preserved(current: dict, original: dict) -> None:
    assert {key: value for key, value in current.items() if key != "advice"} == {
        key: value for key, value in original.items() if key != "advice"
    }


@pytest.fixture
def advisor() -> FakeAdvisor:
    return FakeAdvisor()


@pytest.fixture
def advice_settings() -> Settings:
    return Settings(
        _env_file=None,
        ai_provider="openai",
        ai_model="fake-advice-model",
        ai_api_key=None,
        aws_enabled=False,
        aws_allow_deployments=False,
    )


@pytest.fixture
def advice_client(client_factory, advisor: FakeAdvisor, advice_settings: Settings):
    return client_factory(advisor=advisor, settings=advice_settings)


def test_slow_initial_generation_cannot_overwrite_a_later_regeneration(
    client_factory,
    tmp_path: Path,
) -> None:
    started = Event()
    release = Event()
    original = _advice("Respuesta inicial lenta")
    recent = _advice("Informe regenerado mas reciente")

    class ConcurrentAdvisor(ArchitectureAdvisor):
        def recommend(self, payload: AdviceInput) -> ArchitectureAdvice:
            if current_thread().name.startswith("slow-initial"):
                started.set()
                if not release.wait(timeout=5):
                    raise AssertionError("The parallel generation did not complete")
                return original
            return recent

    repository = SqliteCaseRepository(tmp_path / "concurrent-advice.sqlite3")
    advisor = ConcurrentAdvisor()
    client = client_factory(repository=repository, advisor=advisor)
    case = _create_case(client)
    service = ArchitectureAdviceService(repository, advisor, "fake", "fake-model")
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="slow-initial") as executor:
        pending = executor.submit(service.generate, case["id"])
        try:
            assert started.wait(timeout=5)
            service.generate(case["id"])
            regenerated = service.generate(case["id"], regenerate=True)
        finally:
            release.set()
        assert pending.result(timeout=5) == regenerated
    saved = repository.get(case["id"])
    assert saved is not None
    assert saved.advice == regenerated
    assert saved.advice.content.summary == recent.summary
    _assert_case_preserved(saved.model_dump(mode="json"), case)


@pytest.mark.parametrize("scenario", ["new", "existing"])
def test_advice_uses_saved_confirmed_input_and_preserves_catalog(
    advice_client, advisor: FakeAdvisor, scenario: str
) -> None:
    original = _create_case(advice_client, scenario)
    assert original["advice"] is None
    assert advisor.calls == []

    response = advice_client.post(f"/api/cases/{original['id']}/advice", json={})

    assert response.status_code == 200
    report = response.json()
    assert report["provider"] == "openai"
    assert report["model"] == "fake-advice-model"
    assert datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00")).utcoffset() == (
        UTC.utcoffset(None)
    )
    assert report["content"]["recommendations"][0]["evidence"] == ["no perder ventas"]
    assert bool(report["content"]["current_architecture_assessment"]) == (scenario == "existing")
    assert len(advisor.calls) == 1
    assert advisor.calls[0].model_dump(mode="json") == {
        "confirmed": original["confirmed"],
        "catalog_recommendation": original["recommendation"],
    }
    reloaded = advice_client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == report


def test_advice_persists_across_apps_and_cached_posts_do_not_call_model(
    client_factory, tmp_path: Path, advisor: FakeAdvisor, advice_settings: Settings
) -> None:
    path = tmp_path / "shared-advice.sqlite3"
    client = client_factory(
        repository=SqliteCaseRepository(path), advisor=advisor, settings=advice_settings
    )
    original = _create_case(client, "existing")
    endpoint = f"/api/cases/{original['id']}/advice"
    first = client.post(endpoint, json={})
    assert first.status_code == 200
    assert len(advisor.calls) == 1
    for request in ({}, {"regenerate": False}):
        cached = client.post(endpoint, json=request)
        assert cached.status_code == 200
        assert cached.json() == first.json()
    assert len(advisor.calls) == 1

    other_advisor = FakeAdvisor()
    other_advisor.error = AssertionError("A cached report must not invoke AI")
    other = client_factory(
        repository=SqliteCaseRepository(path), advisor=other_advisor, settings=advice_settings
    )
    reloaded = other.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == first.json()
    cached = other.post(endpoint, json={"regenerate": False})
    assert cached.status_code == 200
    assert cached.json() == first.json()
    assert other_advisor.calls == []
    listed = other.get("/api/cases")
    assert listed.status_code == 200
    assert listed.json()[0]["scenario"] == "existing"
    assert listed.json()[0]["architecture"] == original["recommendation"]["architecture"]


def test_explicit_regeneration_replaces_only_the_report(
    advice_client, advisor: FakeAdvisor
) -> None:
    original = _create_case(advice_client, "existing")
    endpoint = f"/api/cases/{original['id']}/advice"
    first = advice_client.post(endpoint, json={})
    assert first.status_code == 200
    advisor.content = _advice(
        "Informe revisado", "Se necesita probar la recuperacion del servidor."
    )

    regenerated = advice_client.post(endpoint, json={"regenerate": True})

    assert regenerated.status_code == 200
    assert regenerated.json()["content"] == advisor.content.model_dump(mode="json")
    assert regenerated.json()["content"] != first.json()["content"]
    assert len(advisor.calls) == 2
    assert advisor.calls[0] == advisor.calls[1]
    reloaded = advice_client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == regenerated.json()
    assert advice_client.post(endpoint, json={}).json() == regenerated.json()
    assert len(advisor.calls) == 2


@pytest.mark.parametrize(
    "error_type", [AIProviderError, AIResponseValidationError, AIConfigurationError]
)
def test_failed_regeneration_keeps_previous_report_and_catalog(
    advice_client, advisor: FakeAdvisor, error_type: type[Exception]
) -> None:
    original = _create_case(advice_client, "existing")
    endpoint = f"/api/cases/{original['id']}/advice"
    first = advice_client.post(endpoint, json={})
    assert first.status_code == 200
    advisor.error = error_type(PRIVATE_DETAIL)

    failed = advice_client.post(endpoint, json={"regenerate": True})

    assert failed.status_code == 503
    assert PRIVATE_DETAIL not in failed.text
    assert "A/B/C" in failed.json()["detail"]
    assert len(advisor.calls) == 2
    reloaded = advice_client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == first.json()
    assert advice_client.post(endpoint, json={}).json() == first.json()
    assert len(advisor.calls) == 2


@pytest.mark.parametrize("regenerate", [False, True])
def test_missing_case_returns_404_without_ai(advice_client, advisor, regenerate: bool) -> None:
    response = advice_client.post("/api/cases/missing-case/advice", json={"regenerate": regenerate})

    assert response.status_code == 404
    assert response.json()["detail"] == "No encontramos ese caso."
    assert advisor.calls == []


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"catalog_recommendation": {"architecture": "architecture_c"}}, id="catalog"),
        pytest.param({"recommendation": {"architecture": "architecture_c"}}, id="recommendation"),
        pytest.param({"advice": {"summary": "Reporte impuesto"}}, id="advice"),
        pytest.param({"confirmed": {"business_case": "Caso impuesto"}}, id="confirmed"),
        pytest.param({"project_context": {"scenario": "new"}}, id="context"),
        *[
            pytest.param({"regenerate": value}, id=f"regenerate-{value!r}")
            for value in ("true", "false", 1, 0, None, [], {})
        ],
    ],
)
def test_request_cannot_override_saved_data_or_coerce_regenerate(
    advice_client, advisor: FakeAdvisor, body: dict
) -> None:
    original = _create_case(advice_client)

    response = advice_client.post(f"/api/cases/{original['id']}/advice", json=body)

    assert response.status_code == 422
    assert advisor.calls == []
    reloaded = advice_client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    assert reloaded.json() == original


@pytest.mark.parametrize(
    ("scenario", "assessment"),
    [("existing", None), ("new", "La IA invento una arquitectura actual.")],
)
def test_service_rejects_assessment_incompatible_with_scenario_without_saving(
    tmp_path: Path, client_factory, advisor: FakeAdvisor, scenario: str, assessment: str | None
) -> None:
    repository = SqliteCaseRepository(tmp_path / "invalid-assessment.sqlite3")
    client = client_factory(repository=repository, advisor=advisor)
    original = _create_case(client, scenario)
    advisor.content = _advice(assessment=assessment)
    save = Mock(wraps=repository.save_advice)
    repository.save_advice = save
    service = ArchitectureAdviceService(repository, advisor, "fake-provider", "fake-model")

    with pytest.raises(AIResponseValidationError):
        service.generate(original["id"])

    save.assert_not_called()
    assert len(advisor.calls) == 1
    reloaded = client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    assert reloaded.json() == original


def test_wrong_assessment_during_regeneration_keeps_cached_report(
    advice_client, advisor: FakeAdvisor
) -> None:
    original = _create_case(advice_client, "existing")
    endpoint = f"/api/cases/{original['id']}/advice"
    first = advice_client.post(endpoint, json={})
    assert first.status_code == 200
    advisor.content = _advice(assessment=None)

    response = advice_client.post(endpoint, json={"regenerate": True})

    assert response.status_code == 503
    reloaded = advice_client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == first.json()


@pytest.mark.parametrize("operation", ["get", "save_advice"])
def test_storage_errors_are_friendly_and_keep_previous_report(
    client_factory, tmp_path: Path, advisor: FakeAdvisor, monkeypatch, operation: str
) -> None:
    path = tmp_path / "storage-error.sqlite3"
    repository = SqliteCaseRepository(path)
    client = client_factory(repository=repository, advisor=advisor)
    original = _create_case(client, "existing")
    endpoint = f"/api/cases/{original['id']}/advice"
    previous = client.post(endpoint, json={})
    assert previous.status_code == 200
    advisor.content = _advice("Informe que no debe persistirse", "Evaluacion del servidor actual.")
    failing = Mock(side_effect=CaseStorageError(PRIVATE_DETAIL))
    with monkeypatch.context() as patcher:
        patcher.setattr(repository, operation, failing)
        response = client.post(endpoint, json={"regenerate": True})

    assert response.status_code == 503
    assert PRIVATE_DETAIL not in response.text
    assert response.json()["detail"].startswith("No fue posible guardar o consultar")
    failing.assert_called_once()
    assert len(advisor.calls) == (1 if operation == "get" else 2)
    reloaded = client.get(f"/api/cases/{original['id']}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == previous.json()
    persisted = SqliteCaseRepository(path).get(original["id"])
    assert persisted is not None
    assert persisted.advice.model_dump(mode="json") == previous.json()


def test_legacy_database_without_advice_or_context_opens_and_gains_persistent_advice(
    client_factory, tmp_path: Path, advisor: FakeAdvisor, advice_settings: Settings
) -> None:
    path = tmp_path / "legacy.sqlite3"
    request = BusinessCaseConfirmationRequest.model_validate(_request())
    confirmed = ConfirmedBusinessCase(**request.model_dump())
    legacy_confirmed = confirmed.model_dump(mode="json", exclude={"project_context"})
    recommendation = evaluate(confirmed.requirements, confirmed.priority_ranking).model_dump(
        mode="json"
    )
    # A historical message proves that opening the database does not recompute the catalog.
    recommendation["message"] = "Recomendacion historica que debe conservarse literalmente."
    case_id = "a" * 32
    created_at = "2025-01-02T03:04:05+00:00"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE cases (id TEXT PRIMARY KEY, created_at TEXT NOT NULL,"
            " architecture TEXT NOT NULL, trade_off INTEGER NOT NULL, business_case TEXT NOT NULL,"
            " confirmed_json TEXT NOT NULL, recommendation_json TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                case_id,
                created_at,
                recommendation["architecture"],
                int(recommendation["trade_off"]),
                BUSINESS_CASE,
                json.dumps(legacy_confirmed),
                json.dumps(recommendation),
            ),
        )
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'case_advice'"
            ).fetchone()
            is None
        )
    client = client_factory(
        repository=SqliteCaseRepository(path), advisor=advisor, settings=advice_settings
    )

    response = client.get(f"/api/cases/{case_id}")

    assert response.status_code == 200
    original = response.json()
    assert original["confirmed"] == {
        **legacy_confirmed,
        "project_context": {"scenario": "new", "current_architecture": None},
    }
    assert original["recommendation"] == recommendation
    assert original["advice"] is None
    listed = client.get("/api/cases")
    assert listed.status_code == 200
    assert listed.json()[0]["scenario"] == "new"
    assert listed.json()[0]["architecture"] == recommendation["architecture"]
    assert advisor.calls == []
    generated = client.post(f"/api/cases/{case_id}/advice", json={})
    assert generated.status_code == 200
    assert generated.json()["content"]["current_architecture_assessment"] is None
    assert len(advisor.calls) == 1
    other_advisor = FakeAdvisor()
    other_advisor.error = AssertionError("Legacy advice must be persisted")
    other = client_factory(
        repository=SqliteCaseRepository(path), advisor=other_advisor, settings=advice_settings
    )
    reloaded = other.get(f"/api/cases/{case_id}")
    assert reloaded.status_code == 200
    _assert_case_preserved(reloaded.json(), original)
    assert reloaded.json()["advice"] == generated.json()
    cached = other.post(f"/api/cases/{case_id}/advice", json={})
    assert cached.status_code == 200
    assert cached.json() == generated.json()
    assert other_advisor.calls == []
    with sqlite3.connect(path) as connection:
        raw = connection.execute(
            "SELECT confirmed_json, recommendation_json FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
    assert json.loads(raw[0]) == legacy_confirmed
    assert json.loads(raw[1]) == recommendation
