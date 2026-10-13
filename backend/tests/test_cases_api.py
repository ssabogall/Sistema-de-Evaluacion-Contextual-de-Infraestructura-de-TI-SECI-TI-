from pathlib import Path

from app.persistence.models import CaseRecord, CaseSummary
from app.persistence.repository import CaseRepository, CaseStorageError
from app.persistence.sqlite_repository import SqliteCaseRepository
from tests.helpers import analysis_payload, requirement

COMPLETE_RANKING = {
    "never_stop_working": 1,
    "protect_information": 2,
    "fast_under_load": 3,
    "lowest_cost": 4,
}


def _request(**overrides: object) -> dict[str, object]:
    analysis = analysis_payload(
        service_interruption_tolerance=requirement("low", "detected", ["no puede caerse"]),
        business_continuity_criticality=requirement("high", "detected", ["se detienen ventas"]),
    )
    request: dict[str, object] = {
        "business_case": analysis["business_case"],
        "requirements": analysis["requirements"],
    }
    request.update(overrides)
    return request


class FailingRepository(CaseRepository):
    def save(self, record: CaseRecord) -> None:
        raise CaseStorageError("disco lleno")

    def get(self, case_id: str) -> CaseRecord | None:
        raise CaseStorageError("disco ilegible")

    def list_recent(self, limit: int = 50) -> list[CaseSummary]:
        raise CaseStorageError("disco ilegible")


def test_create_case_returns_id_confirmed_case_and_recommendation(client_factory) -> None:
    response = client_factory().post("/api/cases", json=_request(priority_ranking=COMPLETE_RANKING))

    assert response.status_code == 201
    body = response.json()
    assert len(body["id"]) == 32
    assert body["confirmed"]["status"] == "confirmed"
    assert body["confirmed"]["priority_ranking"] == {**COMPLETE_RANKING}
    assert body["recommendation"]["weights_source"] == "ranking"
    assert body["recommendation"]["architecture"] in {
        "architecture_a",
        "architecture_b",
        "architecture_c",
    }
    assert body["recommendation"]["message"].startswith("Se recomienda ")


def test_case_without_ranking_uses_equal_weights(client_factory) -> None:
    response = client_factory().post("/api/cases", json=_request())

    assert response.status_code == 201
    assert response.json()["recommendation"]["weights_source"] == "equal"


def test_get_case_returns_the_saved_case(client_factory) -> None:
    client = client_factory()
    created = client.post("/api/cases", json=_request(priority_ranking=COMPLETE_RANKING)).json()

    response = client.get(f"/api/cases/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_case_survives_a_new_application_instance(client_factory, tmp_path: Path) -> None:
    repository = SqliteCaseRepository(tmp_path / "shared.sqlite3")
    created = client_factory(repository=repository).post("/api/cases", json=_request()).json()

    other_client = client_factory(repository=SqliteCaseRepository(tmp_path / "shared.sqlite3"))

    assert other_client.get(f"/api/cases/{created['id']}").json() == created


def test_unknown_case_returns_404(client_factory) -> None:
    response = client_factory().get("/api/cases/no-existe")

    assert response.status_code == 404
    assert response.json()["detail"] == "No encontramos ese caso."


def test_list_cases_returns_newest_first(client_factory) -> None:
    client = client_factory()
    first = client.post("/api/cases", json=_request()).json()
    second = client.post("/api/cases", json=_request()).json()

    response = client.get("/api/cases")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second["id"], first["id"]]
    assert set(response.json()[0]) == {
        "id",
        "created_at",
        "business_case_excerpt",
        "architecture",
        "trade_off",
    }


def test_create_case_rejects_repeated_ranking_positions(client_factory) -> None:
    response = client_factory().post(
        "/api/cases", json=_request(priority_ranking={"never_stop_working": 1, "lowest_cost": 1})
    )

    assert response.status_code == 422


def test_storage_failures_use_a_friendly_message_without_internal_details(
    client_factory,
) -> None:
    client = client_factory(repository=FailingRepository())

    responses = [
        client.post("/api/cases", json=_request()),
        client.get("/api/cases"),
        client.get("/api/cases/cualquiera"),
    ]

    for response in responses:
        assert response.status_code == 503
        assert "disco" not in response.text
        assert response.json()["detail"].startswith("No fue posible guardar o consultar")
