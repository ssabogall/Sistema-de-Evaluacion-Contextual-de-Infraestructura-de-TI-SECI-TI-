from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.decision_engine.architectures import ArchitectureId


class AwsConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["connected", "disabled"]
    region: str
    account_id: str | None = None
    principal_arn: str | None = None
    deployments_enabled: bool = False
    message: str


class DeploymentTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    architecture: ArchitectureId


class DeploymentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    logical_resource_id: str
    resource_status: str
    reason: str | None = None


class DeploymentState(DeploymentTarget):
    region: str
    stack_name: str
    stack_id: str | None = None
    status: str = "NOT_DEPLOYED"
    outputs: dict[str, str] = Field(default_factory=dict)
    events: list[DeploymentEvent] = Field(default_factory=list)
    last_updated_at: datetime | None = None


class CreateDeploymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_costs: Literal[True]
