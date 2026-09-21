from abc import ABC, abstractmethod

from app.schemas.business_case import BusinessCaseAnalysis


class AIExtractionError(Exception):
    """Base error for failures that can be shown as a generic analysis error."""


class AIConfigurationError(AIExtractionError):
    """The provider is not configured."""


class AIProviderError(AIExtractionError):
    """The provider could not complete the request."""


class AIResponseValidationError(AIExtractionError):
    """The provider response was empty or failed schema validation."""


class AIRequirementExtractor(ABC):
    @abstractmethod
    def extract_requirements(self, business_case: str) -> BusinessCaseAnalysis:
        """Extract the six canonical requirements from a business case."""
