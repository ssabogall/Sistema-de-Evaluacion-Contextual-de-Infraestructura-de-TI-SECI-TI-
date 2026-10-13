from datetime import UTC, datetime
from uuid import uuid4

from app.decision_engine.engine import evaluate
from app.persistence.models import CaseRecord, CaseSummary
from app.persistence.repository import CaseRepository
from app.schemas.business_case import ConfirmedBusinessCase


class CaseService:
    """Evalua un caso confirmado con el motor y lo guarda para poder consultarlo despues."""

    def __init__(self, repository: CaseRepository) -> None:
        self._repository = repository

    def create(self, confirmed: ConfirmedBusinessCase) -> CaseRecord:
        record = CaseRecord(
            id=uuid4().hex,
            created_at=datetime.now(UTC),
            confirmed=confirmed,
            recommendation=evaluate(confirmed.requirements, confirmed.priority_ranking),
        )
        self._repository.save(record)
        return record

    def get(self, case_id: str) -> CaseRecord | None:
        return self._repository.get(case_id)

    def list_recent(self, limit: int = 50) -> list[CaseSummary]:
        return self._repository.list_recent(limit)
