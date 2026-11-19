from collections.abc import Callable, Iterator
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch
from uuid import UUID

import boto3
import pytest
from botocore.endpoint import Endpoint
from botocore.exceptions import ProfileNotFound
from botocore.stub import ANY, Stubber

from app.aws.cloudformation import CloudFormationGateway
from app.aws.errors import (
    AwsConfigurationError,
    AwsConflictError,
    AwsPermissionError,
    AwsProviderError,
)
from app.config import Settings
from app.decision_engine.architectures import ArchitectureId
from app.schemas.deployment import DeploymentEvent, DeploymentState, DeploymentTarget

ACCOUNT_ID = "123456789012"
REGION = "us-east-1"
ACCESS_KEY = "offline-access-key"
SECRET_KEY = "offline-secret-key"
SESSION_TOKEN = "offline-session-token"
PROVIDER_MESSAGE = f"private provider detail {ACCESS_KEY} {SECRET_KEY} {SESSION_TOKEN}"
CREATED_AT = datetime(2026, 1, 2, 12, tzinfo=UTC)
UPDATED_AT = datetime(2026, 1, 2, 13, tzinfo=UTC)
TARGET = DeploymentTarget(case_id="a" * 32, architecture=ArchitectureId.A)


def aws_settings(**overrides: Any) -> Settings:
    options = {
        "aws_enabled": True,
        "aws_allow_deployments": True,
        "aws_region": REGION,
        "aws_profile": None,
        "aws_access_key_id": ACCESS_KEY,
        "aws_secret_access_key": SECRET_KEY,
        "aws_session_token": SESSION_TOKEN,
        "aws_expected_account_id": ACCOUNT_ID,
        "aws_stack_prefix": "offline-test",
        "aws_instance_type": "t2.micro",
    }
    options.update(overrides)
    return Settings(_env_file=None, **options)


def stack_name(target: DeploymentTarget) -> str:
    return f"offline-test-{target.case_id}"


def stack_id(target: DeploymentTarget) -> str:
    return (
        f"arn:aws:cloudformation:{REGION}:{ACCOUNT_ID}:stack/{stack_name(target)}/"
        "11111111-2222-4333-8444-555555555555"
    )


def template_body(architecture: ArchitectureId) -> str:
    return (
        "AWSTemplateFormatVersion: '2010-09-09'\n"
        f"Description: Offline fixture for {architecture.value}\n"
        "Parameters:\n"
        "  CaseId: {Type: String}\n"
        "  InstanceType: {Type: String}\n"
        "Resources:\n"
        "  Vpc: {Type: 'AWS::EC2::VPC', Properties: {CidrBlock: '10.0.0.0/16'}}\n"
    )


class StubbedAws:
    def __init__(self, settings: Settings, templates_root: Path) -> None:
        self.settings = settings
        # Explicit dummy credentials prevent boto3 from consulting credential providers or IMDS.
        boto_session = boto3.Session(
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            aws_session_token=SESSION_TOKEN,
            region_name=REGION,
        )
        self.sts = boto_session.client("sts")
        self.cloudformation = boto_session.client("cloudformation")
        self.sts_stub = Stubber(self.sts)
        self.cf_stub = Stubber(self.cloudformation)
        self.session = Mock()
        clients = {"sts": self.sts, "cloudformation": self.cloudformation}
        self.session.client.side_effect = lambda service, **kwargs: clients[service]
        self.session_factory = Mock(return_value=self.session)
        self.gateway = CloudFormationGateway(
            settings,
            session_factory=self.session_factory,
            templates_root=templates_root,
        )

    def identity(self, account_id: str = ACCOUNT_ID) -> None:
        self.sts_stub.add_response(
            "get_caller_identity",
            {
                "Account": account_id,
                "Arn": f"arn:aws:sts::{account_id}:assumed-role/OfflineRole/test",
                "UserId": "OFFLINE:test",
            },
            {},
        )

    def absent(self, target: DeploymentTarget = TARGET) -> None:
        self.cf_stub.add_client_error(
            "describe_stacks",
            service_error_code="ValidationError",
            service_message=f"Stack with id {stack_name(target)} does not exist",
            expected_params={"StackName": stack_name(target)},
        )

    def stack(
        self,
        target: DeploymentTarget = TARGET,
        status: str = "CREATE_COMPLETE",
        **overrides: Any,
    ) -> None:
        stack = {
            "StackName": stack_name(target),
            "StackId": stack_id(target),
            "CreationTime": CREATED_AT,
            "StackStatus": status,
            "Tags": [
                {"Key": "Application", "Value": "SECI-TI"},
                {"Key": "CaseId", "Value": target.case_id},
                {"Key": "Architecture", "Value": target.architecture.value},
            ],
        }
        stack.update(overrides)
        self.cf_stub.add_response(
            "describe_stacks",
            {"Stacks": [stack]},
            {"StackName": stack_name(target)},
        )

    def events(
        self,
        target: DeploymentTarget = TARGET,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.cf_stub.add_response(
            "describe_stack_events",
            {"StackEvents": events or []},
            {"StackName": stack_id(target)},
        )

    def create_params(self, target: DeploymentTarget = TARGET) -> dict[str, Any]:
        return {
            "StackName": stack_name(target),
            "TemplateBody": template_body(target.architecture),
            "Parameters": [
                {"ParameterKey": "CaseId", "ParameterValue": target.case_id},
                {"ParameterKey": "InstanceType", "ParameterValue": "t2.micro"},
            ],
            "Tags": [
                {"Key": "Application", "Value": "SECI-TI"},
                {"Key": "CaseId", "Value": target.case_id},
                {"Key": "Architecture", "Value": target.architecture.value},
            ],
            "ClientRequestToken": ANY,
            "OnFailure": "ROLLBACK",
            "TimeoutInMinutes": 20,
        }

    def creation(self, target: DeploymentTarget = TARGET) -> None:
        self.cf_stub.add_response(
            "validate_template",
            {},
            {"TemplateBody": template_body(target.architecture)},
        )
        self.cf_stub.add_response(
            "create_stack",
            {"StackId": stack_id(target)},
            self.create_params(target),
        )


@pytest.fixture(autouse=True)
def offline_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        Endpoint,
        "make_request",
        Mock(side_effect=AssertionError("AWS network requests are forbidden in these tests")),
    )


@pytest.fixture
def aws(tmp_path: Path) -> Iterator[Callable[..., StubbedAws]]:
    templates_root = tmp_path / "templates"
    for architecture, directory in (
        (ArchitectureId.A, "architecture-a"),
        (ArchitectureId.B, "architecture-b"),
        (ArchitectureId.C, "architecture-c"),
    ):
        directory_path = templates_root / directory
        directory_path.mkdir(parents=True)
        (directory_path / "template.yaml").write_text(template_body(architecture), encoding="utf-8")

    harnesses = []
    with ExitStack() as stack:

        def make(settings: Settings | None = None, **overrides: Any) -> StubbedAws:
            harness = StubbedAws(settings or aws_settings(**overrides), templates_root)
            stack.callback(harness.sts.close)
            stack.callback(harness.cloudformation.close)
            stack.enter_context(harness.sts_stub)
            stack.enter_context(harness.cf_stub)
            harnesses.append(harness)
            return harness

        yield make
        for harness in harnesses:
            harness.sts_stub.assert_no_pending_responses()
            harness.cf_stub.assert_no_pending_responses()


def test_disabled_connection_does_not_invoke_session_factory(aws) -> None:
    stub = aws(aws_enabled=False)

    connection = stub.gateway.connection()

    assert connection.status == "disabled"
    assert connection.region == REGION
    assert connection.account_id is None
    assert connection.principal_arn is None
    assert connection.deployments_enabled is False
    stub.session_factory.assert_not_called()


def test_connection_verifies_identity_and_forwards_explicit_credentials(aws) -> None:
    stub = aws()
    stub.identity()

    connection = stub.gateway.connection()

    assert connection.status == "connected"
    assert connection.account_id == ACCOUNT_ID
    assert connection.principal_arn == f"arn:aws:sts::{ACCOUNT_ID}:assumed-role/OfflineRole/test"
    assert connection.deployments_enabled is True
    stub.session_factory.assert_called_once_with(
        region_name=REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    assert [call.args[0] for call in stub.session.client.call_args_list] == ["sts"]


def test_environment_key_pair_and_token_are_forwarded(aws, monkeypatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", ACCESS_KEY)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", SECRET_KEY)
    monkeypatch.setenv("AWS_SESSION_TOKEN", SESSION_TOKEN)
    settings = aws_settings()
    options = settings.model_dump(
        exclude={
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_session_token",
        }
    )
    stub = aws(settings=Settings(_env_file=None, **options))
    stub.identity()

    stub.gateway.connection()

    stub.session_factory.assert_called_once_with(
        region_name=REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )


def test_profile_is_forwarded_without_explicit_credentials(aws) -> None:
    stub = aws(
        aws_profile="offline-profile",
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
    )
    stub.identity()

    stub.gateway.connection()

    stub.session_factory.assert_called_once_with(region_name=REGION, profile_name="offline-profile")


@pytest.mark.parametrize(
    "overrides",
    [
        {"aws_secret_access_key": None},
        {"aws_access_key_id": None},
        {"aws_access_key_id": None, "aws_secret_access_key": None},
        {"aws_profile": "offline-profile"},
    ],
)
def test_invalid_credential_combinations_fail_before_session_creation(aws, overrides) -> None:
    stub = aws(**overrides)

    with pytest.raises(AwsConfigurationError) as error:
        stub.gateway.connection()

    assert SECRET_KEY not in str(error.value)
    assert SESSION_TOKEN not in str(error.value)
    stub.session_factory.assert_not_called()


@pytest.mark.parametrize("operation", ["connection", "get", "create", "delete"])
def test_unexpected_account_blocks_all_cloudformation_access(aws, operation) -> None:
    stub = aws()
    stub.identity(account_id="999999999999")

    with pytest.raises(AwsPermissionError, match="AWS_EXPECTED_ACCOUNT_ID"):
        if operation == "connection":
            stub.gateway.connection()
        else:
            getattr(stub.gateway, operation)(TARGET)

    assert [call.args[0] for call in stub.session.client.call_args_list] == ["sts"]


@pytest.mark.parametrize(
    "code,error_type",
    [
        ("ExpiredToken", AwsConfigurationError),
        ("InvalidClientTokenId", AwsConfigurationError),
        ("SignatureDoesNotMatch", AwsConfigurationError),
        ("AccessDenied", AwsPermissionError),
        ("AccessDeniedException", AwsPermissionError),
        ("ServiceUnavailable", AwsProviderError),
    ],
)
def test_sts_errors_are_classified_without_exposing_provider_details(aws, code, error_type) -> None:
    stub = aws()
    stub.sts_stub.add_client_error(
        "get_caller_identity",
        service_error_code=code,
        service_message=PROVIDER_MESSAGE,
        expected_params={},
    )

    with pytest.raises(error_type) as error:
        stub.gateway.connection()

    for secret in (ACCESS_KEY, SECRET_KEY, SESSION_TOKEN, PROVIDER_MESSAGE):
        assert secret not in str(error.value)


def test_botocore_configuration_errors_are_sanitized(aws) -> None:
    stub = aws()
    stub.session_factory.side_effect = ProfileNotFound(profile=SECRET_KEY)

    with pytest.raises(AwsConfigurationError) as error:
        stub.gateway.connection()

    assert SECRET_KEY not in str(error.value)


@pytest.mark.parametrize("operation", ["create", "delete"])
def test_mutations_require_opt_in_before_contacting_aws(aws, operation) -> None:
    stub = aws(aws_allow_deployments=False)

    with pytest.raises(AwsPermissionError, match="AWS_ALLOW_DEPLOYMENTS"):
        getattr(stub.gateway, operation)(TARGET)

    stub.session_factory.assert_not_called()


def test_get_returns_typed_events_allowed_outputs_and_update_time(aws) -> None:
    stub = aws()
    stub.identity()
    outputs = {
        "ApplicationUrl": "https://example.invalid",
        "VpcId": "vpc-offline",
        "InstanceId": "i-offline",
        "LoadBalancerFullName": "app/offline/123",
        "AutoScalingGroupName": "offline-asg",
    }
    stub.stack(
        Outputs=[
            {"OutputKey": key, "OutputValue": value}
            for key, value in {**outputs, "SecretOutput": SECRET_KEY}.items()
        ],
        LastUpdatedTime=UPDATED_AT,
    )
    events = [
        {
            "StackId": stack_id(TARGET),
            "StackName": stack_name(TARGET),
            "EventId": f"event-{index}",
            "Timestamp": UPDATED_AT,
            "LogicalResourceId": f"Resource{index}",
            "ResourceStatus": "CREATE_COMPLETE",
            **({"ResourceStatusReason": "Resource creation complete"} if index == 0 else {}),
        }
        for index in range(17)
    ]
    stub.events(events=events)

    state = stub.gateway.get(TARGET)

    assert isinstance(state, DeploymentState)
    assert state.case_id == TARGET.case_id
    assert state.architecture == ArchitectureId.A
    assert state.region == REGION
    assert state.stack_id == stack_id(TARGET)
    assert state.status == "CREATE_COMPLETE"
    assert state.outputs == outputs
    assert state.last_updated_at == UPDATED_AT
    assert len(state.events) == 15
    assert all(isinstance(event, DeploymentEvent) for event in state.events)
    assert [event.logical_resource_id for event in state.events] == [
        f"Resource{index}" for index in range(15)
    ]
    assert state.events[0].timestamp == UPDATED_AT
    assert state.events[0].reason == "Resource creation complete"
    assert state.events[1].reason is None
    assert SECRET_KEY not in state.model_dump_json()


def test_get_falls_back_to_stack_creation_time(aws) -> None:
    stub = aws()
    stub.identity()
    stub.stack()
    stub.events()

    assert stub.gateway.get(TARGET).last_updated_at == CREATED_AT


@pytest.mark.parametrize("architecture", list(ArchitectureId))
def test_create_validates_selected_template_and_sends_safe_stack_parameters(
    aws, architecture
) -> None:
    stub = aws()
    target = DeploymentTarget(case_id=TARGET.case_id, architecture=architecture)
    stub.identity()
    stub.absent(target)
    stub.creation(target)

    with patch.object(
        stub.cloudformation,
        "create_stack",
        wraps=stub.cloudformation.create_stack,
    ) as create_stack:
        state = stub.gateway.create(target)

    assert state.status == "CREATE_IN_PROGRESS"
    assert state.stack_id == stack_id(target)
    assert state.architecture == architecture
    assert state.outputs == {}
    assert state.events == []
    assert isinstance(state.last_updated_at, datetime)
    assert state.last_updated_at.tzinfo is not None
    assert UUID(create_stack.call_args.kwargs["ClientRequestToken"]).version == 4


@pytest.mark.parametrize("status", ["CREATE_IN_PROGRESS", "CREATE_COMPLETE"])
def test_duplicate_create_returns_existing_stack_without_validation_or_creation(
    aws, status
) -> None:
    stub = aws()
    for _ in range(2):
        stub.identity()
        stub.stack(status=status)
        stub.events()

    first = stub.gateway.create(TARGET)
    second = stub.gateway.create(TARGET)

    assert first == second
    assert second.status == status
    assert second.stack_id == stack_id(TARGET)


@pytest.mark.parametrize(
    "status", ["ROLLBACK_COMPLETE", "UPDATE_IN_PROGRESS", "DELETE_IN_PROGRESS"]
)
def test_create_rejects_an_existing_stack_in_an_incompatible_state(aws, status) -> None:
    stub = aws()
    stub.identity()
    stub.stack(status=status)
    stub.events()

    with pytest.raises(AwsConflictError):
        stub.gateway.create(TARGET)


@pytest.mark.parametrize("operation", ["get", "create", "delete"])
@pytest.mark.parametrize("foreign_key", ["Application", "CaseId", "Architecture", "missing"])
def test_foreign_or_untagged_stacks_block_read_create_and_delete(
    aws, operation, foreign_key
) -> None:
    stub = aws()
    stub.identity()
    tags = {
        "Application": "SECI-TI",
        "CaseId": TARGET.case_id,
        "Architecture": TARGET.architecture.value,
    }
    if foreign_key == "missing":
        tags = {}
    else:
        tags[foreign_key] = "foreign-value"
    stub.stack(Tags=[{"Key": key, "Value": value} for key, value in tags.items()])

    with pytest.raises(AwsConflictError):
        getattr(stub.gateway, operation)(TARGET)


def test_delete_uses_verified_stack_arn_and_request_token(aws) -> None:
    stub = aws()
    stub.identity()
    stub.stack(Outputs=[{"OutputKey": "ApplicationUrl", "OutputValue": "https://example.invalid"}])
    stub.events()
    stub.cf_stub.add_response(
        "delete_stack",
        {},
        {"StackName": stack_id(TARGET), "ClientRequestToken": ANY},
    )

    with patch.object(
        stub.cloudformation,
        "delete_stack",
        wraps=stub.cloudformation.delete_stack,
    ) as delete_stack:
        state = stub.gateway.delete(TARGET)

    assert state.status == "DELETE_IN_PROGRESS"
    assert state.stack_id == stack_id(TARGET)
    assert state.outputs == {}
    assert isinstance(state.last_updated_at, datetime)
    assert UUID(delete_stack.call_args.kwargs["ClientRequestToken"]).version == 4


@pytest.mark.parametrize("operation", ["get", "delete"])
def test_missing_stack_returns_not_deployed_idempotently(aws, operation) -> None:
    stub = aws()
    for _ in range(2):
        stub.identity()
        stub.absent()

    states = [getattr(stub.gateway, operation)(TARGET) for _ in range(2)]

    assert states[0] == states[1]
    assert states[0].status == "NOT_DEPLOYED"
    assert states[0].stack_id is None
    assert states[0].outputs == {}
    assert states[0].events == []


@pytest.mark.parametrize("status", ["DELETE_IN_PROGRESS", "DELETE_COMPLETE"])
def test_duplicate_delete_does_not_send_another_delete_request(aws, status) -> None:
    stub = aws()
    for _ in range(2):
        stub.identity()
        stub.stack(status=status)
        stub.events()

    assert stub.gateway.delete(TARGET) == stub.gateway.delete(TARGET)


@pytest.mark.parametrize("status", ["CREATE_IN_PROGRESS", "UPDATE_IN_PROGRESS"])
def test_delete_blocks_stacks_with_another_operation_in_progress(aws, status) -> None:
    stub = aws()
    stub.identity()
    stub.stack(status=status)
    stub.events()

    with pytest.raises(AwsConflictError):
        stub.gateway.delete(TARGET)


@pytest.mark.parametrize("operation", ["get", "create", "delete"])
@pytest.mark.parametrize(
    "code,message,error_type",
    [
        ("ValidationError", "Invalid stack name", AwsProviderError),
        ("ResourceNotFoundException", "Stack does not exist", AwsProviderError),
        ("AccessDenied", "Stack does not exist", AwsPermissionError),
    ],
)
def test_describe_errors_are_not_mistaken_for_a_missing_stack(
    aws,
    operation,
    code,
    message,
    error_type,
) -> None:
    stub = aws()
    stub.identity()
    stub.cf_stub.add_client_error(
        "describe_stacks",
        service_error_code=code,
        service_message=f"{message} {PROVIDER_MESSAGE}",
        expected_params={"StackName": stack_name(TARGET)},
    )

    with pytest.raises(error_type) as error:
        getattr(stub.gateway, operation)(TARGET)

    assert PROVIDER_MESSAGE not in str(error.value)


def test_template_validation_failure_prevents_create(aws) -> None:
    stub = aws()
    stub.identity()
    stub.absent()
    stub.cf_stub.add_client_error(
        "validate_template",
        service_error_code="ValidationError",
        service_message=PROVIDER_MESSAGE,
        expected_params={"TemplateBody": template_body(TARGET.architecture)},
    )

    with pytest.raises(AwsProviderError) as error:
        stub.gateway.create(TARGET)

    assert PROVIDER_MESSAGE not in str(error.value)


@pytest.mark.parametrize(
    "code,error_type",
    [
        ("AlreadyExistsException", AwsConflictError),
        ("TokenAlreadyExistsException", AwsConflictError),
        ("AccessDenied", AwsPermissionError),
        ("ExpiredToken", AwsConfigurationError),
        ("ValidationError", AwsProviderError),
    ],
)
def test_create_stack_errors_preserve_error_class_and_hide_provider_details(
    aws,
    code,
    error_type,
) -> None:
    stub = aws()
    stub.identity()
    stub.absent()
    stub.cf_stub.add_response(
        "validate_template",
        {},
        {"TemplateBody": template_body(TARGET.architecture)},
    )
    stub.cf_stub.add_client_error(
        "create_stack",
        service_error_code=code,
        service_message=PROVIDER_MESSAGE,
        expected_params=stub.create_params(),
    )

    with pytest.raises(error_type) as error:
        stub.gateway.create(TARGET)

    assert PROVIDER_MESSAGE not in str(error.value)


def test_delete_validation_error_is_not_swallowed_as_a_missing_stack(aws) -> None:
    stub = aws()
    stub.identity()
    stub.stack()
    stub.events()
    stub.cf_stub.add_client_error(
        "delete_stack",
        service_error_code="ValidationError",
        service_message=PROVIDER_MESSAGE,
        expected_params={"StackName": stack_id(TARGET), "ClientRequestToken": ANY},
    )

    with pytest.raises(AwsProviderError) as error:
        stub.gateway.delete(TARGET)

    assert PROVIDER_MESSAGE not in str(error.value)


def test_event_permission_errors_are_not_swallowed(aws) -> None:
    stub = aws()
    stub.identity()
    stub.stack()
    stub.cf_stub.add_client_error(
        "describe_stack_events",
        service_error_code="AccessDenied",
        service_message=PROVIDER_MESSAGE,
        expected_params={"StackName": stack_id(TARGET)},
    )

    with pytest.raises(AwsPermissionError):
        stub.gateway.get(TARGET)


def test_empty_stack_response_is_a_provider_error(aws) -> None:
    stub = aws()
    stub.identity()
    stub.cf_stub.add_response("describe_stacks", {"Stacks": []}, {"StackName": stack_name(TARGET)})

    with pytest.raises(AwsProviderError):
        stub.gateway.get(TARGET)
