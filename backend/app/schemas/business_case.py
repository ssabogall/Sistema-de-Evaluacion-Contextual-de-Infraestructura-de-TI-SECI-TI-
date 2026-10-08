from enum import Enum, StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RequirementStatus(StrEnum):
    DETECTED = "detected"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"

class StandardLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class DemandPattern(StrEnum):
    CONSTANT = "constant"
    PREDICTABLE_PEAKS = "predictable_peaks"
    UNPREDICTABLE_PEAKS = "unpredictable_peaks"
    UNKNOWN = "unknown"


class RequirementKey(StrEnum):
    SERVICE_INTERRUPTION_TOLERANCE = "service_interruption_tolerance"
    BUSINESS_CONTINUITY_CRITICALITY = "business_continuity_criticality"
    INFORMATION_SENSITIVITY = "information_sensitivity"
    AVAILABLE_BUDGET = "available_budget"
    DEMAND_PATTERN = "demand_pattern"
    EXPECTED_LOAD_VOLUME = "expected_load_volume"


class ServiceInterruptionTolerance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


ValueEnum = TypeVar("ValueEnum", bound=Enum)


class Requirement(BaseModel, Generic[ValueEnum]):
    model_config = ConfigDict(extra="forbid")

    value: ValueEnum
    status: RequirementStatus
    evidence: list[str] = Field(default_factory=list)

    @field_validator("value", mode="before")
    @classmethod
    def normalize_safe_enum_equivalents(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().lower().replace("-", "_").replace(" ", "_")

    @field_validator("evidence")
    @classmethod
    def clean_evidence(cls, evidence: list[str]) -> list[str]:
        cleaned = [fragment.strip() for fragment in evidence if fragment.strip()]
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def validate_status_consistency(self) -> "Requirement[ValueEnum]":
        value = self.value.value
        if self.status == RequirementStatus.UNKNOWN:
            if value != "unknown" or self.evidence:
                raise ValueError("unknown requires value=unknown and no evidence")
        if self.status == RequirementStatus.DETECTED and value == "unknown":
            raise ValueError("detected cannot use value=unknown")
        if self.status == RequirementStatus.CONFLICT:
            if value != "unknown" or len(self.evidence) < 2:
                raise ValueError(
                    "conflict requires value=unknown and at least two evidence fragments"
                )
        return self


class Requirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_interruption_tolerance: Requirement[ServiceInterruptionTolerance]
    business_continuity_criticality: Requirement[StandardLevel]
    information_sensitivity: Requirement[StandardLevel]
    available_budget: Requirement[StandardLevel]
    demand_pattern: Requirement[DemandPattern]
    expected_load_volume: Requirement[StandardLevel]

    def canonical_items(self) -> list[tuple[RequirementKey, Requirement[Enum]]]:
        return [(key, getattr(self, key.value)) for key in RequirementKey]


class AdditionalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_description: str | None = None
    expected_users: int | None = Field(default=None, ge=0)
    concurrent_users: int | None = Field(default=None, ge=0)
    requests_per_second: float | None = Field(default=None, ge=0)
    expected_growth: str | None = None
    geographical_scope: str | None = None
    explicit_availability_target: str | None = None
    explicit_response_time_target: str | None = None
    budget_raw: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=12)
    budget_period: str | None = Field(default=None, max_length=40)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class AnalyzeBusinessCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=10, max_length=20_000)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class BusinessCaseAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_case: str = Field(min_length=1, max_length=20_000)
    requirements: Requirements
    additional_context: AdditionalContext = Field(default_factory=AdditionalContext)
    missing_requirements: list[RequirementKey] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_user_confirmation: Literal[True] = True

    @model_validator(mode="after")
    def synchronize_missing_requirements(self) -> "BusinessCaseAnalysis":
        self.missing_requirements = [
            key
            for key, requirement in self.requirements.canonical_items()
            if requirement.value.value == "unknown"
        ]
        return self


class BusinessCaseConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_case: str = Field(min_length=1, max_length=20_000)
    requirements: Requirements
    additional_context: AdditionalContext = Field(default_factory=AdditionalContext)


class ConfirmedBusinessCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["confirmed"] = "confirmed"
    business_case: str
    requirements: Requirements
    additional_context: AdditionalContext
