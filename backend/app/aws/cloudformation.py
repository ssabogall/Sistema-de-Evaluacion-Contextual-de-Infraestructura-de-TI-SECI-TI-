from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.aws.errors import (
    AwsConfigurationError,
    AwsConflictError,
    AwsPermissionError,
    AwsProviderError,
)
from app.config import PROJECT_ROOT, Settings
from app.decision_engine.architectures import ArchitectureId
from app.schemas.deployment import (
    AwsConnection,
    DeploymentEvent,
    DeploymentState,
    DeploymentTarget,
)

TEMPLATE_PATHS = {
    ArchitectureId.A: Path("architecture-a/template.yaml"),
    ArchitectureId.B: Path("architecture-b/template.yaml"),
    ArchitectureId.C: Path("architecture-c/template.yaml"),
}
AUTH_ERRORS = {
    "ExpiredToken",
    "ExpiredTokenException",
    "InvalidClientTokenId",
    "InvalidToken",
    "UnrecognizedClientException",
    "SignatureDoesNotMatch",
    "RequestExpired",
}
PERMISSION_ERRORS = {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}
OUTPUT_KEYS = {
    "ApplicationUrl",
    "VpcId",
    "InstanceId",
    "LoadBalancerFullName",
    "AutoScalingGroupName",
}


class AwsGateway(Protocol):
    def connection(self) -> AwsConnection: ...

    def get(self, target: DeploymentTarget) -> DeploymentState: ...

    def create(self, target: DeploymentTarget) -> DeploymentState: ...

    def delete(self, target: DeploymentTarget) -> DeploymentState: ...


def _provider_error(exc: BotoCoreError | ClientError) -> Exception:
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in AUTH_ERRORS:
            return AwsConfigurationError(
                "Las credenciales de AWS no son validas o expiraron. "
                "Renueva tambien AWS_SESSION_TOKEN si usas Learner Lab y reinicia el backend."
            )
        if code in PERMISSION_ERRORS:
            return AwsPermissionError(
                "AWS denego el acceso. Revisa los permisos del rol para CloudFormation "
                "y los recursos de la arquitectura."
            )
        if code in {"AlreadyExistsException", "TokenAlreadyExistsException"}:
            return AwsConflictError(
                "El despliegue ya existe. Actualiza su estado antes de continuar."
            )
        return AwsProviderError(
            "AWS no pudo completar la operacion. Revisa los eventos del stack "
            "y los limites de tu cuenta antes de reintentar."
        )
    return AwsConfigurationError(
        "No fue posible conectar con AWS. Revisa las credenciales, el perfil, "
        "la region y la conexion de red del backend."
    )


class CloudFormationGateway:
    def __init__(
        self,
        settings: Settings,
        session_factory: Callable[..., Any] = boto3.Session,
        templates_root: Path = PROJECT_ROOT / "infrastructure",
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._templates_root = templates_root
        self._client_config = Config(
            connect_timeout=5,
            read_timeout=15,
            retries={"mode": "standard", "total_max_attempts": 2},
        )

    def _session(self) -> Any:
        if not self._settings.aws_enabled:
            raise AwsConfigurationError("Activa AWS_ENABLED en el backend para conectar con AWS.")
        key = self._settings.aws_access_key_id
        secret = self._settings.aws_secret_access_key
        token = self._settings.aws_session_token
        if bool(key) != bool(secret) or (token and not key):
            raise AwsConfigurationError(
                "Configura AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY juntos; "
                "las credenciales temporales tambien necesitan AWS_SESSION_TOKEN."
            )
        if self._settings.aws_profile and key:
            raise AwsConfigurationError(
                "Configura un perfil AWS o claves explicitas, solo una opcion."
            )
        options: dict[str, str] = {"region_name": self._settings.aws_region}
        if self._settings.aws_profile:
            options["profile_name"] = self._settings.aws_profile
        if key and secret:
            options["aws_access_key_id"] = key.get_secret_value()
            options["aws_secret_access_key"] = secret.get_secret_value()
            if token:
                options["aws_session_token"] = token.get_secret_value()
        return self._session_factory(**options)

    def _identity(self, session: Any) -> dict[str, Any]:
        identity = session.client("sts", config=self._client_config).get_caller_identity()
        expected = self._settings.aws_expected_account_id
        if expected and identity["Account"] != expected:
            raise AwsPermissionError(
                "La cuenta AWS conectada no coincide con AWS_EXPECTED_ACCOUNT_ID. "
                "Selecciona las credenciales correctas antes de continuar."
            )
        return identity

    def connection(self) -> AwsConnection:
        if not self._settings.aws_enabled:
            return AwsConnection(
                status="disabled",
                region=self._settings.aws_region,
                message="La conexion AWS esta desactivada en este entorno.",
            )
        try:
            identity = self._identity(self._session())
        except (BotoCoreError, ClientError) as exc:
            raise _provider_error(exc) from exc
        return AwsConnection(
            status="connected",
            region=self._settings.aws_region,
            account_id=identity["Account"],
            principal_arn=identity["Arn"],
            deployments_enabled=self._settings.aws_allow_deployments,
            message="Conexion AWS verificada. Los permisos de despliegue se validan al operar.",
        )

    def _client(self) -> Any:
        session = self._session()
        self._identity(session)
        return session.client("cloudformation", config=self._client_config)

    def _empty(self, target: DeploymentTarget) -> DeploymentState:
        return DeploymentState(
            **target.model_dump(),
            region=self._settings.aws_region,
            stack_name=f"{self._settings.aws_stack_prefix}-{target.case_id}",
        )

    @staticmethod
    def _tags(target: DeploymentTarget) -> dict[str, str]:
        return {
            "Application": "SECI-TI",
            "CaseId": target.case_id,
            "Architecture": target.architecture.value,
        }

    def _read(self, client: Any, target: DeploymentTarget) -> DeploymentState:
        state = self._empty(target)
        try:
            response = client.describe_stacks(StackName=state.stack_name)
        except ClientError as exc:
            error = exc.response.get("Error", {})
            if error.get("Code") == "ValidationError" and "does not exist" in error.get(
                "Message", ""
            ):
                return state
            raise
        stacks = response.get("Stacks", [])
        if not stacks:
            raise AwsProviderError("AWS devolvio una respuesta de stack incompleta.")
        stack = stacks[0]
        tags = {tag["Key"]: tag["Value"] for tag in stack.get("Tags", [])}
        if any(tags.get(key) != value for key, value in self._tags(target).items()):
            raise AwsConflictError(
                "El stack encontrado no pertenece a este caso de SECI-TI. "
                "No se modificara; revisa AWS_STACK_PREFIX."
            )
        events = client.describe_stack_events(StackName=stack["StackId"]).get("StackEvents", [])
        return DeploymentState.model_validate(
            {
                **state.model_dump(),
                "stack_id": stack["StackId"],
                "status": stack["StackStatus"],
                "outputs": {
                    item["OutputKey"]: item["OutputValue"]
                    for item in stack.get("Outputs", [])
                    if item["OutputKey"] in OUTPUT_KEYS
                },
                "last_updated_at": stack.get("LastUpdatedTime", stack.get("CreationTime")),
                "events": [
                    DeploymentEvent(
                        timestamp=event["Timestamp"],
                        logical_resource_id=event["LogicalResourceId"],
                        resource_status=event["ResourceStatus"],
                        reason=event.get("ResourceStatusReason"),
                    )
                    for event in events[:15]
                ],
            }
        )

    def get(self, target: DeploymentTarget) -> DeploymentState:
        try:
            return self._read(self._client(), target)
        except (BotoCoreError, ClientError) as exc:
            raise _provider_error(exc) from exc

    def _allow_mutation(self) -> None:
        if not self._settings.aws_allow_deployments:
            raise AwsPermissionError(
                "Los cambios en AWS estan desactivados. Activa AWS_ALLOW_DEPLOYMENTS "
                "en el backend para crear o eliminar recursos."
            )

    def create(self, target: DeploymentTarget) -> DeploymentState:
        self._allow_mutation()
        try:
            client = self._client()
            state = self._read(client, target)
            if state.status not in {"NOT_DEPLOYED", "DELETE_COMPLETE"}:
                if state.status in {"CREATE_IN_PROGRESS", "CREATE_COMPLETE"}:
                    return state
                raise AwsConflictError(
                    "El stack ya existe. Espera a que termine o elimina el despliegue "
                    "anterior antes de crear otro."
                )
            try:
                template = (self._templates_root / TEMPLATE_PATHS[target.architecture]).read_text(
                    encoding="utf-8"
                )
            except OSError as exc:
                raise AwsConfigurationError(
                    "No se encontro la plantilla de la arquitectura en el backend."
                ) from exc
            client.validate_template(TemplateBody=template)
            response = client.create_stack(
                StackName=state.stack_name,
                TemplateBody=template,
                Parameters=[
                    {"ParameterKey": "CaseId", "ParameterValue": target.case_id},
                    {
                        "ParameterKey": "InstanceType",
                        "ParameterValue": self._settings.aws_instance_type,
                    },
                ],
                Tags=[{"Key": key, "Value": value} for key, value in self._tags(target).items()],
                ClientRequestToken=uuid4().hex,
                OnFailure="ROLLBACK",
                TimeoutInMinutes=20,
            )
            return state.model_copy(
                update={
                    "stack_id": response["StackId"],
                    "status": "CREATE_IN_PROGRESS",
                    "last_updated_at": datetime.now(UTC),
                    "outputs": {},
                    "events": [],
                }
            )
        except (BotoCoreError, ClientError) as exc:
            raise _provider_error(exc) from exc

    def delete(self, target: DeploymentTarget) -> DeploymentState:
        self._allow_mutation()
        try:
            client = self._client()
            state = self._read(client, target)
            if state.status in {"NOT_DEPLOYED", "DELETE_COMPLETE", "DELETE_IN_PROGRESS"}:
                return state
            if state.status.endswith("_IN_PROGRESS"):
                raise AwsConflictError(
                    "Espera a que termine la operacion antes de eliminar el stack."
                )
            client.delete_stack(StackName=state.stack_id, ClientRequestToken=uuid4().hex)
            return state.model_copy(
                update={
                    "status": "DELETE_IN_PROGRESS",
                    "last_updated_at": datetime.now(UTC),
                    "outputs": {},
                }
            )
        except (BotoCoreError, ClientError) as exc:
            raise _provider_error(exc) from exc
