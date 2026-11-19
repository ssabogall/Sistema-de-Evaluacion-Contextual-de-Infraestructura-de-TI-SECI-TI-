"""RF-04 y RNF-01: el motor elige la arquitectura esperada en los casos curados.

Umbral de RNF-01: al menos 90 % de aciertos sobre 15-20 casos claros. La prueba es
agregada a proposito: un fallo aislado no rompe la suite mientras se cumpla el umbral,
pero el mensaje de error lista todos los casos fallidos para revisarlos.
"""

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.engine import Recommendation, evaluate
from app.schemas.business_case import PriorityRanking, Requirements
from tests.curated_engine_cases import CURATED_ENGINE_CASES, CuratedEngineCase
from tests.helpers import analysis_payload, requirement

MIN_ACCURACY = 0.90
MIN_CASES = 15
MAX_CASES = 20


def build_inputs(case: CuratedEngineCase) -> tuple[Requirements, PriorityRanking]:
    """Convierte un caso curado en las mismas entradas que recibe el motor en la API."""
    payload = analysis_payload(
        case.description,
        **{
            key.value: requirement(level, "detected", [case.description])
            for key, level in case.requirement_levels().items()
        },
    )
    requirements = Requirements.model_validate(payload["requirements"])
    ranking = PriorityRanking(**case.ranking_positions())
    return requirements, ranking


def evaluate_case(case: CuratedEngineCase) -> Recommendation:
    return evaluate(*build_inputs(case))


def test_curated_set_size_and_coverage() -> None:
    """RNF-01 pide entre 15 y 20 casos claros; deben cubrir las tres arquitecturas."""
    assert MIN_CASES <= len(CURATED_ENGINE_CASES) <= MAX_CASES
    assert {case.expected for case in CURATED_ENGINE_CASES} == set(ArchitectureId)
    case_ids = [case.case_id for case in CURATED_ENGINE_CASES]
    assert len(case_ids) == len(set(case_ids)), "case_id repetido"


def test_every_curated_case_returns_a_single_catalog_architecture() -> None:
    """RF-04, criterio 1: dado un contexto de ejemplo se retorna una unica arquitectura."""
    for case in CURATED_ENGINE_CASES:
        recommendation = evaluate_case(case)
        assert recommendation.architecture in set(ArchitectureId), case.case_id
        assert recommendation.runner_up != recommendation.architecture, case.case_id


def test_engine_accuracy_on_curated_cases_meets_rnf_01() -> None:
    """RF-04, criterio 2, y RNF-01: >= 90 % de coincidencia con la arquitectura esperada."""
    misses = []
    for case in CURATED_ENGINE_CASES:
        obtained = evaluate_case(case).architecture
        if obtained != case.expected:
            misses.append(f"{case.case_id}: esperada {case.expected}, obtenida {obtained}")

    hits = len(CURATED_ENGINE_CASES) - len(misses)
    accuracy = hits / len(CURATED_ENGINE_CASES)
    assert accuracy >= MIN_ACCURACY, (
        f"Precision {accuracy:.0%} ({hits}/{len(CURATED_ENGINE_CASES)}) por debajo de "
        f"{MIN_ACCURACY:.0%}. Fallos: {misses}"
    )
