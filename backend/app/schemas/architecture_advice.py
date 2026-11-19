from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.decision_engine.engine import Recommendation
from app.schemas.business_case import ConfirmedBusinessCase

AdviceText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]


class AdviceCategory(StrEnum):
    ARCHITECTURE = "architecture"
    APPLICATION = "application"
    DATA = "data"
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    OPERATIONS = "operations"
    COST = "cost"


class AdviceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImprovementSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: AdviceText
    category: AdviceCategory
    priority: AdviceLevel
    effort: AdviceLevel
    recommendation: AdviceText
    rationale: AdviceText
    expected_benefit: AdviceText
    tradeoffs: AdviceText
    evidence: list[AdviceText] = Field(default_factory=list, max_length=8)


class ArchitectureAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: AdviceText
    description: AdviceText
    suitable_when: AdviceText
    tradeoffs: AdviceText
    migration_steps: list[AdviceText] = Field(min_length=1, max_length=8)


class ArchitectureAdvice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: AdviceText
    current_architecture_assessment: AdviceText | None = None
    recommendations: list[ImprovementSuggestion] = Field(min_length=1, max_length=12)
    alternatives: list[ArchitectureAlternative] = Field(min_length=1, max_length=4)
    next_steps: list[AdviceText] = Field(min_length=1, max_length=8)
    assumptions: list[AdviceText] = Field(default_factory=list, max_length=10)
    open_questions: list[AdviceText] = Field(default_factory=list, max_length=10)


class SavedArchitectureAdvice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    provider: str
    model: str | None
    content: ArchitectureAdvice


class AdviceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: ConfirmedBusinessCase
    catalog_recommendation: Recommendation


class GenerateAdviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regenerate: bool = Field(default=False, strict=True)
