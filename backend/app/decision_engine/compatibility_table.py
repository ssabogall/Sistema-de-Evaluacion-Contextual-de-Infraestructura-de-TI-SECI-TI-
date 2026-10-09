"""Tabla de compatibilidad SAW: que tan bien encaja cada nivel de cada
variable con cada arquitectura, escala -2 a +3.

Fuente de los valores: docs/motor_de_reglas_puntaje_ponderado.md,
seccion 3. Si cambian un valor aqui, cambienlo tambien alla -- o se
desincronizan.
"""

from app.decision_engine.architectures import ArchitectureId
from app.schemas.business_case import (
    RequirementKey,
    StandardLevel,
    DemandPattern,
)

class CompatibilityLookupError(Exception):
    """No existe entrada en la tabla para la combinacion pedida."""
    pass

COMPATIBILITY_TABLE = {
    RequirementKey.SERVICE_INTERRUPTION_TOLERANCE: {
        StandardLevel.HIGH: {
            ArchitectureId.A: 3,  
            ArchitectureId.B: 1,  
            ArchitectureId.C: -1,  
        },
        StandardLevel.MEDIUM: {
            ArchitectureId.A: 0,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1,  
            },
        StandardLevel.LOW: {
            ArchitectureId.A: -2,
            ArchitectureId.B: 0,
            ArchitectureId.C: 3,
            },  
    },
    RequirementKey.BUSINESS_CONTINUITY_CRITICALITY: {
        StandardLevel.LOW: {
            ArchitectureId.A: 2,
            ArchitectureId.B: 1,
            ArchitectureId.C: -1
        },
        StandardLevel.MEDIUM: {
            ArchitectureId.A: 0,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1
        },
        StandardLevel.HIGH: {
            ArchitectureId.A: -2,
            ArchitectureId.B: 1,
            ArchitectureId.C: 3
        },
        
    },
    RequirementKey.INFORMATION_SENSITIVITY: {
        StandardLevel.LOW: {
            ArchitectureId.A: 1,
            ArchitectureId.B: 1,
            ArchitectureId.C: 1
        },
        StandardLevel.MEDIUM: {
            ArchitectureId.A: 0,
            ArchitectureId.B: 1,
            ArchitectureId.C: 1
        },
        StandardLevel.HIGH: {
            ArchitectureId.A: -1,
            ArchitectureId.B: 0,
            ArchitectureId.C: 2
        },
    },       
    RequirementKey.AVAILABLE_BUDGET: {
        StandardLevel.LOW: {
            ArchitectureId.A: 3,
            ArchitectureId.B: 1,
            ArchitectureId.C: -2
        },
        StandardLevel.MEDIUM: {
            ArchitectureId.A: 1,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1
        },
        StandardLevel.HIGH: {
            ArchitectureId.A: -1,
            ArchitectureId.B: 1,
            ArchitectureId.C: 3
        }
    },
    RequirementKey.DEMAND_PATTERN: {
        DemandPattern.CONSTANT:{
            ArchitectureId.A: 2,
            ArchitectureId.B: 0,
            ArchitectureId.C: 0
        },
        DemandPattern.PREDICTABLE_PEAKS:{
            ArchitectureId.A: -1,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1
        },
        DemandPattern.UNPREDICTABLE_PEAKS:{
            ArchitectureId.A: -2,
            ArchitectureId.B: 1,
            ArchitectureId.C: 2
        }
    },
    RequirementKey.EXPECTED_LOAD_VOLUME: {
        StandardLevel.LOW:{
            ArchitectureId.A: 2,
            ArchitectureId.B: 0,
            ArchitectureId.C: -1
        },
        StandardLevel.MEDIUM:{
            ArchitectureId.A: 0,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1
        },
        StandardLevel.HIGH:{
            ArchitectureId.A: -2,
            ArchitectureId.B: 1,
            ArchitectureId.C: 2
        }
    },
}

def get_score(
    key: RequirementKey,
    level: str,
    architecture: ArchitectureId,
) -> float:
    """Devuelve el puntaje de compatibilidad (-2..+3) de una arquitectura
    para el nivel dado de una variable.

    `level` se recibe como str: los enums del esquema son StrEnum, asi que
    StandardLevel, DemandPattern y ServiceInterruptionTolerance se comparan
    por su valor de texto.

    Lanza CompatibilityLookupError si la combinacion no existe (nivel
    equivocado para esa variable, o 'unknown'). El caso 'unknown' se
    resuelve ANTES, en scoring.py (constante 0.5).
    """
    try:
        return float(COMPATIBILITY_TABLE[key][level][architecture])
    except KeyError as exc:
        raise CompatibilityLookupError(
            f"Sin entrada en la tabla: key={key!r}, level={level!r}, "
            f"architecture={architecture!r}"
        ) from exc