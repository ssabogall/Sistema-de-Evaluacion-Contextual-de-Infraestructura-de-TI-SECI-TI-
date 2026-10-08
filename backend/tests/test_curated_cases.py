import pytest

from app.schemas.business_case import BusinessCaseAnalysis
from tests.helpers import analysis_payload, requirement

CURATED_CASES = [
    (
        "Necesitamos una aplicacion interna para aproximadamente 50 empleados. Su uso sera estable durante el horario laboral. Si deja de funcionar durante algunas horas no tendria un impacto grave y tenemos un presupuesto bastante limitado.",
        {
            "service_interruption_tolerance": requirement("high", "detected", ["algunas horas"]),
            "business_continuity_criticality": requirement(
                "low", "detected", ["no tendria un impacto grave"]
            ),
            "available_budget": requirement("low", "detected", ["presupuesto bastante limitado"]),
            "demand_pattern": requirement("constant", "detected", ["uso sera estable"]),
        },
        {"expected_users": 50},
    ),
    (
        "Esperamos aproximadamente 5.000 usuarios y durante promociones podemos recibir aumentos repentinos de trafico que son dificiles de predecir. Podemos tolerar algunos minutos de interrupcion y tenemos un presupuesto moderado.",
        {
            "service_interruption_tolerance": requirement(
                "medium", "detected", ["algunos minutos de interrupcion"]
            ),
            "available_budget": requirement("medium", "detected", ["presupuesto moderado"]),
            "demand_pattern": requirement(
                "unpredictable_peaks", "detected", ["dificiles de predecir"]
            ),
        },
        {"expected_users": 5000},
    ),
    (
        "Esta plataforma procesa las ventas principales de la compania. Si deja de funcionar nuestra operacion comercial se detiene. Necesitamos que permanezca disponible practicamente todo el tiempo y tenemos presupuesto suficiente para priorizar la continuidad.",
        {
            "service_interruption_tolerance": requirement(
                "near_zero", "detected", ["disponible practicamente todo el tiempo"]
            ),
            "business_continuity_criticality": requirement(
                "high", "detected", ["nuestra operacion comercial se detiene"]
            ),
            "available_budget": requirement("high", "detected", ["presupuesto suficiente"]),
        },
        {},
    ),
    (
        "Queremos crear una nueva aplicacion para nuestros clientes.",
        {},
        {},
    ),
    (
        "Nuestro sistema almacenara informacion financiera y datos personales de clientes. Esperamos un trafico relativamente estable.",
        {
            "information_sensitivity": requirement(
                "high", "detected", ["informacion financiera y datos personales"]
            ),
            "demand_pattern": requirement(
                "constant", "detected", ["trafico relativamente estable"]
            ),
        },
        {},
    ),
    (
        "La aplicacion no es critica para la empresa, pero si deja de funcionar nuestras ventas se detienen completamente.",
        {
            "business_continuity_criticality": requirement(
                "unknown",
                "conflict",
                ["no es critica para la empresa", "nuestras ventas se detienen completamente"],
            ),
        },
        {},
    ),
]


@pytest.mark.parametrize("business_case,requirements,additional_context", CURATED_CASES)
def test_six_curated_contracts_are_valid(
    business_case: str,
    requirements: dict,
    additional_context: dict,
) -> None:
    payload = analysis_payload(business_case, **requirements)
    payload["additional_context"] = additional_context

    analysis = BusinessCaseAnalysis.model_validate(payload)

    assert len(analysis.requirements.canonical_items()) == 6
    assert analysis.requires_user_confirmation is True
    for key, expected_requirement in requirements.items():
        actual = getattr(analysis.requirements, key)
        assert actual.value.value == expected_requirement["value"]
        assert actual.status.value == expected_requirement["status"]
        assert actual.evidence == expected_requirement["evidence"]
    for key, expected_value in additional_context.items():
        assert getattr(analysis.additional_context, key) == expected_value
