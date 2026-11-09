from datetime import UTC, datetime

from app.ai.architecture_advisor import ArchitectureAdvisor
from app.ai.base import AIResponseValidationError
from app.persistence.repository import CaseRepository
from app.schemas.architecture_advice import AdviceInput, SavedArchitectureAdvice
from app.schemas.project_context import ProjectScenario


class AdviceCaseNotFoundError(Exception):
    pass


class ArchitectureAdviceService:
    def __init__(
        self,
        repository: CaseRepository,
        advisor: ArchitectureAdvisor,
        provider: str,
        model: str | None,
    ) -> None:
        self._repository = repository
        self._advisor = advisor
        self._provider = provider
        self._model = model

    def generate(self, case_id: str, regenerate: bool = False) -> SavedArchitectureAdvice:
        record = self._repository.get(case_id)
        if record is None:
            raise AdviceCaseNotFoundError("No encontramos ese caso.")
        if record.advice is not None and not regenerate:
            return record.advice
        content = self._advisor.recommend(
            AdviceInput(
                confirmed=record.confirmed,
                catalog_recommendation=record.recommendation,
            )
        )
        existing = record.confirmed.project_context.scenario == ProjectScenario.EXISTING
        if existing != (content.current_architecture_assessment is not None):
            raise AIResponseValidationError(
                "The architecture assessment does not match the scenario"
            )
        report = SavedArchitectureAdvice(
            generated_at=datetime.now(UTC),
            provider=self._provider,
            model=self._model,
            content=content,
        )
        return self._repository.save_advice(case_id, report, overwrite=regenerate)
