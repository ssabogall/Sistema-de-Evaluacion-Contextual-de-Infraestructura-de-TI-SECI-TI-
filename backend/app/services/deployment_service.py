from app.aws.cloudformation import AwsGateway
from app.aws.errors import AwsCaseNotFoundError
from app.schemas.deployment import AwsConnection, DeploymentState, DeploymentTarget
from app.services.case_service import CaseService


class DeploymentService:
    def __init__(self, cases: CaseService, gateway: AwsGateway) -> None:
        self._cases = cases
        self._gateway = gateway

    def connection(self) -> AwsConnection:
        return self._gateway.connection()

    def _target(self, case_id: str) -> DeploymentTarget:
        record = self._cases.get(case_id)
        if record is None:
            raise AwsCaseNotFoundError("No encontramos ese caso.")
        return DeploymentTarget(case_id=record.id, architecture=record.recommendation.architecture)

    def get(self, case_id: str) -> DeploymentState:
        return self._gateway.get(self._target(case_id))

    def create(self, case_id: str) -> DeploymentState:
        return self._gateway.create(self._target(case_id))

    def delete(self, case_id: str) -> DeploymentState:
        return self._gateway.delete(self._target(case_id))
