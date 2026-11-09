from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectScenario(StrEnum):
    NEW = "new"
    EXISTING = "existing"


class ProjectContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: ProjectScenario = ProjectScenario.NEW
    current_architecture: str | None = Field(default=None, min_length=10, max_length=20_000)

    @field_validator("current_architecture", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_scenario(self) -> "ProjectContext":
        if self.scenario == ProjectScenario.EXISTING and not self.current_architecture:
            raise ValueError("An existing platform requires its current architecture description")
        if self.scenario == ProjectScenario.NEW and self.current_architecture is not None:
            raise ValueError("A new platform cannot include an existing architecture")
        return self
