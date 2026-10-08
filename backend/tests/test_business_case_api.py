from app.ai.base import AIProviderError, AIResponseValidationError
from app.schemas.business_case import BusinessCaseAnalysis
from tests.helpers import StaticExtractor, analysis_payload, requirement


def test_analyze_returns_typed_analysis_and_original_text(client_factory) -> None:
    detected = BusinessCaseAnalysis.model_validate(
        analysis_payload(demand_pattern=requirement("constant", "detected", ["trafico estable"]))
    )
    client = client_factory(StaticExtractor(detected))
    description = "Esperamos un trafico estable para la aplicacion interna."

    response = client.post("/api/business-cases/analyze", json={"description": description})

    assert response.status_code == 200
    body = response.json()
    assert body["business_case"] == description
    assert body["requirements"]["demand_pattern"]["value"] == "constant"
    assert body["requires_user_confirmation"] is True


def test_confirm_returns_complete_confirmed_object(client_factory) -> None:
    client = client_factory()
    analysis = analysis_payload()
    request = {
        "business_case": analysis["business_case"],
        "requirements": analysis["requirements"],
        "additional_context": analysis["additional_context"],
    }

    response = client.post("/api/business-cases/confirm", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["business_case"] == request["business_case"]
    assert body["requirements"] == request["requirements"]
    assert all(value is None for value in body["additional_context"].values())


def test_provider_error_uses_friendly_public_message(client_factory) -> None:
    client = client_factory(StaticExtractor(error=AIProviderError("internal provider detail")))

    response = client.post(
        "/api/business-cases/analyze",
        json={"description": "Caso suficientemente largo para ser analizado."},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "No fue posible analizar el caso en este momento. Intenta nuevamente."
    )
    assert "internal provider detail" not in response.text


def test_schema_error_uses_same_friendly_message(client_factory) -> None:
    client = client_factory(StaticExtractor(error=AIResponseValidationError("invalid enum")))

    response = client.post(
        "/api/business-cases/analyze",
        json={"description": "Caso suficientemente largo para ser analizado."},
    )

    assert response.status_code == 503
    assert response.json()["detail"].startswith("No fue posible analizar")


def test_request_rejects_unexpected_fields(client_factory) -> None:
    client = client_factory()

    response = client.post(
        "/api/business-cases/analyze",
        json={
            "description": "Caso suficientemente largo para ser analizado.",
            "architecture": "C",
        },
    )

    assert response.status_code == 422
