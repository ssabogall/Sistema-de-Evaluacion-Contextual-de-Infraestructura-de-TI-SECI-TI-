"""Casos curados para medir la precision del motor de decision (RNF-01 / RF-04).

Cada caso describe un negocio claro y la arquitectura que el equipo espera segun
la definicion del catalogo, NO segun lo que devuelve el motor:

- A (basica): una sola instancia; para cargas pequenas y estables, presupuesto
  limitado y negocios que toleran interrupciones.
- B (escalable): ALB + Auto Scaling; para demanda con picos y volumen medio, con
  presupuesto moderado y criticidad media.
- C (resiliente): multi-AZ; para servicios criticos que no toleran caidas, con
  datos sensibles y presupuesto para redundancia.

La arquitectura esperada se fija antes de ejecutar el motor. Si un caso falla, se
revisa el caso o la tabla de compatibilidad con el equipo; nunca se cambia la
expectativa solo para que la prueba pase.
"""

from dataclasses import dataclass

from app.decision_engine.architectures import ArchitectureId
from app.schemas.business_case import BusinessPriorityStatement, RequirementKey

NEVER_STOP = BusinessPriorityStatement.NEVER_STOP_WORKING
LOWEST_COST = BusinessPriorityStatement.LOWEST_COST
FAST = BusinessPriorityStatement.FAST_UNDER_LOAD
PROTECT = BusinessPriorityStatement.PROTECT_INFORMATION


@dataclass(frozen=True)
class CuratedEngineCase:
    """Un caso de negocio ya confirmado y la arquitectura que se espera."""

    case_id: str
    description: str
    # Orden: tolerancia, criticidad, sensibilidad, presupuesto, demanda, volumen.
    levels: tuple[str, str, str, str, str, str]
    # Afirmaciones de negocio de la mas a la menos importante.
    priority_order: tuple[
        BusinessPriorityStatement,
        BusinessPriorityStatement,
        BusinessPriorityStatement,
        BusinessPriorityStatement,
    ]
    expected: ArchitectureId
    rationale: str

    def requirement_levels(self) -> dict[RequirementKey, str]:
        return dict(zip(RequirementKey, self.levels, strict=True))

    def ranking_positions(self) -> dict[str, int]:
        return {
            statement.value: position
            for position, statement in enumerate(self.priority_order, start=1)
        }


CURATED_ENGINE_CASES: tuple[CuratedEngineCase, ...] = (
    # --- Arquitectura A: pequeno, estable, barato, tolerante a caidas ---
    CuratedEngineCase(
        "A-01",
        "Aplicacion interna para 50 empleados en horario laboral.",
        ("high", "low", "low", "low", "constant", "low"),
        (LOWEST_COST, FAST, PROTECT, NEVER_STOP),
        ArchitectureId.A,
        "Uso estable y pequeno; una caida de horas no afecta el negocio.",
    ),
    CuratedEngineCase(
        "A-02",
        "Portafolio web personal con pocas visitas.",
        ("high", "low", "low", "low", "constant", "low"),
        (LOWEST_COST, PROTECT, FAST, NEVER_STOP),
        ArchitectureId.A,
        "Sin datos sensibles ni impacto economico; prima el costo minimo.",
    ),
    CuratedEngineCase(
        "A-03",
        "Prototipo (MVP) para validar una idea con usuarios piloto.",
        ("high", "low", "medium", "low", "constant", "low"),
        (LOWEST_COST, FAST, NEVER_STOP, PROTECT),
        ArchitectureId.A,
        "Etapa de validacion: carga minima y presupuesto muy limitado.",
    ),
    CuratedEngineCase(
        "A-04",
        "Inventario de un club estudiantil.",
        ("high", "low", "low", "low", "constant", "low"),
        (PROTECT, LOWEST_COST, FAST, NEVER_STOP),
        ArchitectureId.A,
        "Aun priorizando proteger la informacion, el contexto es pequeno y estable.",
    ),
    CuratedEngineCase(
        "A-05",
        "Tablero interno de reportes que se consulta pocas veces al dia.",
        ("high", "medium", "low", "low", "constant", "low"),
        (LOWEST_COST, NEVER_STOP, FAST, PROTECT),
        ArchitectureId.A,
        "Criticidad media pero tolera interrupciones y la carga es baja y fija.",
    ),
    CuratedEngineCase(
        "A-06",
        "Catalogo en linea de una tienda de barrio.",
        ("medium", "low", "low", "low", "constant", "low"),
        (LOWEST_COST, FAST, NEVER_STOP, PROTECT),
        ArchitectureId.A,
        "Trafico bajo y constante con presupuesto limitado.",
    ),
    # --- Arquitectura B: picos de demanda, volumen medio, presupuesto moderado ---
    CuratedEngineCase(
        "B-01",
        "Tienda en linea con campanas de temporada (dia de la madre, fin de ano).",
        ("medium", "medium", "medium", "medium", "predictable_peaks", "medium"),
        (FAST, LOWEST_COST, NEVER_STOP, PROTECT),
        ArchitectureId.B,
        "Picos conocidos que exigen elasticidad sin pagar redundancia multi-AZ.",
    ),
    CuratedEngineCase(
        "B-02",
        "Portal de inscripciones universitarias con picos en fechas de matricula.",
        ("medium", "medium", "medium", "medium", "predictable_peaks", "high"),
        (FAST, NEVER_STOP, LOWEST_COST, PROTECT),
        ArchitectureId.B,
        "Volumen alto en ventanas conocidas; una caida corta es tolerable.",
    ),
    CuratedEngineCase(
        "B-03",
        "Pedidos en linea de un restaurante con picos al almuerzo.",
        ("medium", "medium", "low", "medium", "predictable_peaks", "medium"),
        (FAST, LOWEST_COST, NEVER_STOP, PROTECT),
        ArchitectureId.B,
        "Picos diarios predecibles y datos poco sensibles.",
    ),
    CuratedEngineCase(
        "B-04",
        "Venta de boletas para eventos locales anunciados con anticipacion.",
        ("medium", "medium", "low", "medium", "predictable_peaks", "high"),
        (FAST, NEVER_STOP, LOWEST_COST, PROTECT),
        ArchitectureId.B,
        "Rafagas de trafico en lanzamientos conocidos, presupuesto moderado.",
    ),
    CuratedEngineCase(
        "B-05",
        "Sitio de noticias de un medio local con visitas variables.",
        ("medium", "low", "low", "medium", "unpredictable_peaks", "medium"),
        (FAST, LOWEST_COST, NEVER_STOP, PROTECT),
        ArchitectureId.B,
        "Necesita escalar ante noticias virales, pero no es un servicio critico.",
    ),
    CuratedEngineCase(
        "B-06",
        "Aplicacion SaaS de una startup con crecimiento sostenido.",
        ("medium", "medium", "medium", "medium", "predictable_peaks", "medium"),
        (LOWEST_COST, FAST, PROTECT, NEVER_STOP),
        ArchitectureId.B,
        "Equilibrio entre costo y elasticidad en una etapa de crecimiento.",
    ),
    # --- Arquitectura C: critico, sin tolerancia a caidas, datos sensibles ---
    CuratedEngineCase(
        "C-01",
        "Plataforma de pagos en linea.",
        ("low", "high", "high", "high", "unpredictable_peaks", "high"),
        (NEVER_STOP, PROTECT, FAST, LOWEST_COST),
        ArchitectureId.C,
        "Cada minuto caido son transacciones perdidas y los datos son financieros.",
    ),
    CuratedEngineCase(
        "C-02",
        "Sistema de citas de un hospital.",
        ("low", "high", "high", "medium", "constant", "medium"),
        (NEVER_STOP, PROTECT, FAST, LOWEST_COST),
        ArchitectureId.C,
        "Servicio de salud critico con datos personales sensibles.",
    ),
    CuratedEngineCase(
        "C-03",
        "Aplicacion de operaciones internas de un banco.",
        ("low", "high", "high", "high", "constant", "medium"),
        (PROTECT, NEVER_STOP, FAST, LOWEST_COST),
        ArchitectureId.C,
        "Regulacion y continuidad exigen redundancia entre zonas.",
    ),
    CuratedEngineCase(
        "C-04",
        "Comercio electronico nacional en temporada de descuentos masivos.",
        ("low", "high", "medium", "high", "unpredictable_peaks", "high"),
        (NEVER_STOP, FAST, PROTECT, LOWEST_COST),
        ArchitectureId.C,
        "Ventas criticas, picos impredecibles y presupuesto para resiliencia.",
    ),
    CuratedEngineCase(
        "C-05",
        "Sistema de despacho de emergencias.",
        ("low", "high", "medium", "high", "unpredictable_peaks", "medium"),
        (NEVER_STOP, FAST, PROTECT, LOWEST_COST),
        ArchitectureId.C,
        "No puede detenerse; la disponibilidad es un asunto de seguridad publica.",
    ),
    CuratedEngineCase(
        "C-06",
        "Portal de declaracion de impuestos con picos en fechas limite.",
        ("low", "high", "high", "high", "predictable_peaks", "high"),
        (NEVER_STOP, PROTECT, FAST, LOWEST_COST),
        ArchitectureId.C,
        "Servicio publico critico con datos tributarios y volumen alto.",
    ),
)
