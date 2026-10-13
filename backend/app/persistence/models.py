from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.engine import Recommendation
from app.schemas.business_case import ConfirmedBusinessCase


class CaseRecord(BaseModel):
    """Un caso guardado: lo que el usuario confirmo y lo que el motor recomendo."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    confirmed: ConfirmedBusinessCase
    recommendation: Recommendation


class CaseSummary(BaseModel):
    """Fila del listado de casos: lo justo para reconocer un caso sin cargarlo completo."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    business_case_excerpt: str
    architecture: ArchitectureId
    trade_off: bool
