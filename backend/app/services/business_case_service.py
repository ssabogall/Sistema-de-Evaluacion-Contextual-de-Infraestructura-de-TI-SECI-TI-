from app.ai.base import AIRequirementExtractor
from app.schemas.business_case import (
    BusinessCaseAnalysis,
    BusinessCaseConfirmationRequest,
    ConfirmedBusinessCase,
)
from app.schemas.project_context import ProjectContext


class BusinessCaseService:
    def __init__(self, extractor: AIRequirementExtractor) -> None:
        self._extractor = extractor

    def analyze(
        self, description: str, project_context: ProjectContext | None = None
    ) -> BusinessCaseAnalysis:
        context = project_context or ProjectContext()
        analysis = self._extractor.extract_requirements(description, context)
        return BusinessCaseAnalysis.model_validate(
            {**analysis.model_dump(), "business_case": description, "project_context": context}
        )

    def confirm(self, request: BusinessCaseConfirmationRequest) -> ConfirmedBusinessCase:
        return ConfirmedBusinessCase(
            business_case=request.business_case,
            project_context=request.project_context,
            requirements=request.requirements,
            additional_context=request.additional_context,
            priority_ranking=request.priority_ranking,
        )
