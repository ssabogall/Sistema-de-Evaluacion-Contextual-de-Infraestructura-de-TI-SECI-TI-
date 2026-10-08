"""Tabla de compatibilidad SAW: que tan bien encaja cada nivel de cada
variable con cada arquitectura, escala -2 a +3.

Fuente de los valores: docs/motor_de_reglas_puntaje_ponderado.md,
seccion 3. Si cambian un valor aqui, cambienlo tambien alla -- o se
desincronizan.
"""

from app.decision_engine.architectures import ArchitectureId
from app.schemas.business_case import (
    DemandPattern,
    RequirementKey,
    ServiceInterruptionTolerance,
    BusinessContinuityCriticality,
    InformationSensitivity,
    StandardLevel,
)

# TODO (ustedes): completar cada ArchitectureId: ... con el numero exacto
# de la tabla del documento (seccion 3). No inventen valores nuevos aqui
# -- es transcripcion de una decision ya tomada, no una decision nueva.
COMPATIBILITY_TABLE = {
    RequirementKey.SERVICE_INTERRUPTION_TOLERANCE: {
        ServiceInterruptionTolerance.HIGH: {
            ArchitectureId.A: 3,  
            ArchitectureId.B: 1,  
            ArchitectureId.C: -1,  
        },
        ServiceInterruptionTolerance.MEDIUM: {
            ArchitectureId.A: 0,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1,  
            },
        ServiceInterruptionTolerance.LOW: {
            ArchitectureId.A: -2,
            ArchitectureId.B: 0,
            ArchitectureId.C: 3,
            },  
    },
    RequirementKey.BUSINESS_CONTINUITY_CRITICALITY: {
        BusinessContinuityCriticality.HIGH: {
            ArchitectureId.A: 2,
            ArchitectureId.B: 1,
            ArchitectureId.C: -1
        },
        BusinessContinuityCriticality.MEDIUM: {
            ArchitectureId.A: 0,
            ArchitectureId.B: 2,
            ArchitectureId.C: 1
        },
        BusinessContinuityCriticality.LOW: {
            ArchitectureId.A: -2,
            ArchitectureId.B: 1,
            ArchitectureId.C: 3
        },
        
    },
    RequirementKey.INFORMATION_SENSITIVITY: {
        InformationSensitivity.HIGH: {
            ArchitectureId.A: 1,
            ArchitectureId.B: 1,
            ArchitectureId.C: 1
        },
        InformationSensitivity.MEDIUM: {
            ArchitectureId.A: 0,
            ArchitectureId.B: 1,
            ArchitectureId.C: 1
        },
        InformationSensitivity.LOW: {
            ArchitectureId.A: -1,
            ArchitectureId.B: 0,
            ArchitectureId.C: 2
        },
    },       
    RequirementKey.AVAILABLE_BUDGET: {
        
        # TODO: StandardLevel.LOW / MEDIUM / HIGH
    },
    RequirementKey.DEMAND_PATTERN: {
        # TODO: DemandPattern.CONSTANT / PREDICTABLE_PEAKS / UNPREDICTABLE_PEAKS
    },
    RequirementKey.EXPECTED_LOAD_VOLUME: {
        # TODO: StandardLevel.LOW / MEDIUM / HIGH
    },
}


def get_score(key: RequirementKey, level, architecture: ArchitectureId) -> float:
    """TODO (ustedes): implementar.

    Debe buscar COMPATIBILITY_TABLE[key][level][architecture] y
    devolverlo. Pregunta para que resuelvan al escribirla: ¿qué pasa si
    la combinacion no existe en la tabla (ej. un error de escritura en
    el nivel)? Ya tienen el patron de excepciones tipadas en
    app/ai/base.py -- decidan si aqui aplica igual.

    No se encarga del caso 'unknown' -- eso ya lo resolvieron que pasa
    ANTES de llamar aqui (constante 0.5), en scoring.py.
    """
    raise NotImplementedError