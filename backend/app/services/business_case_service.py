from app.ai.base import AIRequirementExtractor
from app.schemas.business_case import (
    BusinessCaseAnalysis,
    BusinessCaseConfirmationRequest,
    ConfirmedBusinessCase,
)


class BusinessCaseService:
    def __init__(self, extractor: AIRequirementExtractor) -> None:
        self._extractor = extractor

    def analyze(self, description: str) -> BusinessCaseAnalysis:
        return self._extractor.extract_requirements(description)

    def confirm(self, request: BusinessCaseConfirmationRequest) -> ConfirmedBusinessCase:
        return ConfirmedBusinessCase(
            business_case=request.business_case,
            requirements=request.requirements,
            additional_context=request.additional_context,
        )
