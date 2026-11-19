from collections.abc import Callable, Iterator
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from botocore.stub import ANY
from fastapi.testclient import TestClient

from app.aws.errors import (
    AwsCaseNotFoundError,
    AwsConfigurationError,
    AwsConflictError,
    AwsPermissionError,
    AwsProviderError,
)
from app.decision_engine.architectures import ArchitectureId
from app.main import create_app
from app.persistence.repository import CaseStorageError
from app.persistence.sqlite_repository import SqliteCaseRepository
from app.schemas.deployment import DeploymentState, DeploymentTarget
from tests.helpers import StaticExtractor, analysis_payload, requirement
from tests.test_aws_cloudformation import (
    ACCESS_KEY,
    ACCOUNT_ID,
    PROVIDER_MESSAGE,
    REGION,
    SECRET_KEY,
    SESSION_TOKEN,
    UPDATED_AT,
    StubbedAws,
    stack_id,
    stack_name,
)
from tests.test_aws_cloudformation import aws as aws
from tests.test_aws_cloudformation import offline_aws as offline_aws


@pytest.fixture
def aws_client(aws, tmp_path: Path) -> Iterator[Callable[..., tuple]]:
    with ExitStack() as stack:

        def make(**settings) -> tuple[TestClient, StubbedAws, SqliteCaseRepository]:
            stub = aws(**settings)
            repository = SqliteCaseRepository(tmp_path / "aws-cases.sqlite3")
            app = create_app(
                extractor=StaticExtractor(),
                settings=stub.settings,
                repository=repository,
                aws_gateway=stub.gateway,
            )
            client = stack.enter_context(TestClient(app))
            return client, stub, repository

        yield make


def save_case(
    client: TestClient, architecture: ArchitectureId = ArchitectureId.A
) -> DeploymentTarget:
    levels = {
        ArchitectureId.A: ("high", "low", "low", "low", "constant", "low"),
        ArchitectureId.B: ("medium", "medium", "medium", "medium", "predictable_peaks", "medium"),
        ArchitectureId.C: ("low", "high", "high", "high", "unpredictable_peaks", "high"),
    }
    keys = (
        "service_interruption_tolerance",
        "business_continuity_criticality",
        "information_sensitivity",
        "available_budget",
        "demand_pattern",
        "expected_load_volume",
    )
    analysis = analysis_payload(
        **{
            key: requirement(value, "detected", [f"Offline requirement: {value}"])
            for key, value in zip(keys, levels[architecture], strict=True)
        }
    )
    response = client.post(
        "/api/cases",
        json={
            "business_case": analysis["business_case"],
            "requirements": analysis["requirements"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["recommendation"]["architecture"] == architecture.value
    return DeploymentTarget(case_id=body["id"], architecture=architecture)


def deployment_url(target: DeploymentTarget) -> str:
    return f"/api/cases/{target.case_id}/deployment"


def deployment_request(client: TestClient, method: str, url: str):
    if method == "POST":
        return client.post(url, json={"confirm_costs": True})
    return client.request(method, url)


def test_disabled_connection_returns_200_without_invoking_aws(aws_client) -> None:
    client, stub, _ = aws_client(aws_enabled=False)

    response = client.get("/api/aws/connection")

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "region": REGION,
        "account_id": None,
        "principal_arn": None,
        "deployments_enabled": False,
        "message": "La conexion AWS esta desactivada en este entorno.",
    }
    stub.session_factory.assert_not_called()


def test_connection_returns_verified_identity_with_mutations_disabled(aws_client) -> None:
    client, stub, _ = aws_client(aws_allow_deployments=False)
    stub.identity()

    response = client.get("/api/aws/connection")

    assert response.status_code == 200
    assert response.json()["status"] == "connected"
    assert response.json()["account_id"] == ACCOUNT_ID
    assert response.json()["principal_arn"].startswith(f"arn:aws:sts::{ACCOUNT_ID}:")
    assert response.json()["deployments_enabled"] is False
    assert SECRET_KEY not in response.text
    assert SESSION_TOKEN not in response.text


@pytest.mark.parametrize("architecture", list(ArchitectureId))
def test_create_returns_202_and_deploys_architecture_from_saved_sqlite_case(
    aws_client,
    architecture,
) -> None:
    client, stub, repository = aws_client()
    target = save_case(client, architecture)
    saved = repository.get(target.case_id)
    assert saved is not None
    assert saved.recommendation.architecture == architecture
    stub.identity()
    stub.absent(target)
    stub.creation(target)

    response = client.post(deployment_url(target), json={"confirm_costs": True})

    assert response.status_code == 202, response.text
    state = DeploymentState.model_validate(response.json())
    assert state.case_id == saved.id
    assert state.architecture == saved.recommendation.architecture
    assert state.status == "CREATE_IN_PROGRESS"
    assert state.stack_name == stack_name(target)
    assert state.stack_id == stack_id(target)
    assert state.last_updated_at is not None
    assert state.outputs == {}
    assert state.events == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"confirm_costs": False},
        {"confirm_costs": "true"},
        {"confirm_costs": True, "architecture": "architecture_c"},
        {"confirm_costs": True, "stack_name": "arbitrary-stack"},
        {
            "confirm_costs": True,
            "stack_id": "arn:aws:cloudformation:us-east-1:999999999999:stack/other/id",
        },
        {"confirm_costs": True, "template_body": "arbitrary-template"},
        {"confirm_costs": True, "parameters": {"InstanceType": "expensive-instance"}},
    ],
)
def test_create_rejects_missing_consent_or_client_controlled_deployment_fields(
    aws_client,
    payload,
) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)

    response = client.post(deployment_url(target), json=payload)

    assert response.status_code == 422
    stub.session_factory.assert_not_called()


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_missing_saved_case_returns_404_without_aws_calls(aws_client, method) -> None:
    client, stub, _ = aws_client()

    response = deployment_request(client, method, f"/api/cases/{'f' * 32}/deployment")

    assert response.status_code == 404
    assert response.json() == {"detail": "No encontramos ese caso."}
    stub.session_factory.assert_not_called()


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_mutations_disabled_returns_403_before_aws_session_creation(aws_client, method) -> None:
    client, stub, _ = aws_client(aws_allow_deployments=False)
    target = save_case(client)

    response = deployment_request(client, method, deployment_url(target))

    assert response.status_code == 403
    assert "AWS_ALLOW_DEPLOYMENTS" in response.json()["detail"]
    stub.session_factory.assert_not_called()


def test_wrong_account_returns_403_before_accessing_cloudformation(aws_client) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    stub.identity(account_id="999999999999")

    response = client.post(deployment_url(target), json={"confirm_costs": True})

    assert response.status_code == 403
    assert "AWS_EXPECTED_ACCOUNT_ID" in response.json()["detail"]
    assert [call.args[0] for call in stub.session.client.call_args_list] == ["sts"]


@pytest.mark.parametrize(
    "code,status_code",
    [
        ("ExpiredToken", 503),
        ("InvalidClientTokenId", 503),
        ("AccessDenied", 403),
        ("ServiceUnavailable", 502),
    ],
)
def test_provider_errors_map_to_http_without_leaking_credentials_in_response_or_logs(
    aws_client,
    caplog,
    code,
    status_code,
) -> None:
    client, stub, _ = aws_client()
    stub.sts_stub.add_client_error(
        "get_caller_identity",
        service_error_code=code,
        service_message=PROVIDER_MESSAGE,
        expected_params={},
    )

    with caplog.at_level("WARNING"):
        response = client.get("/api/aws/connection")

    assert response.status_code == status_code
    assert set(response.json()) == {"detail"}
    assert "AWS operation failed:" in caplog.text
    for private_value in (ACCESS_KEY, SECRET_KEY, SESSION_TOKEN, PROVIDER_MESSAGE):
        assert private_value not in response.text
        assert private_value not in caplog.text


@pytest.mark.parametrize(
    "error_type,status_code",
    [
        (AwsConfigurationError, 503),
        (AwsPermissionError, 403),
        (AwsConflictError, 409),
        (AwsCaseNotFoundError, 404),
        (AwsProviderError, 502),
    ],
)
def test_aws_error_subclasses_keep_their_http_status(aws_client, error_type, status_code) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    public_message = "Public AWS failure"

    with patch.object(stub.gateway, "get", side_effect=error_type(public_message)) as get:
        response = client.get(deployment_url(target))

    assert response.status_code == status_code
    assert response.json() == {"detail": public_message}
    get.assert_called_once_with(target)


def test_get_serializes_typed_events_and_allowlisted_outputs(aws_client) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    stub.identity()
    stub.stack(
        target,
        Outputs=[
            {"OutputKey": "ApplicationUrl", "OutputValue": "https://example.invalid"},
            {"OutputKey": "PrivateOutput", "OutputValue": SECRET_KEY},
        ],
        LastUpdatedTime=UPDATED_AT,
    )
    stub.events(
        target,
        [
            {
                "StackId": stack_id(target),
                "StackName": stack_name(target),
                "EventId": "event-1",
                "Timestamp": UPDATED_AT,
                "LogicalResourceId": "Application",
                "ResourceStatus": "CREATE_COMPLETE",
                "ResourceStatusReason": "Resource creation complete",
            }
        ],
    )

    response = client.get(deployment_url(target))

    assert response.status_code == 200
    state = DeploymentState.model_validate(response.json())
    assert state.status == "CREATE_COMPLETE"
    assert state.architecture == target.architecture
    assert state.outputs == {"ApplicationUrl": "https://example.invalid"}
    assert state.last_updated_at == UPDATED_AT
    assert len(state.events) == 1
    assert state.events[0].timestamp == UPDATED_AT
    assert state.events[0].logical_resource_id == "Application"
    assert state.events[0].resource_status == "CREATE_COMPLETE"
    assert state.events[0].reason == "Resource creation complete"
    assert SECRET_KEY not in response.text


@pytest.mark.parametrize("status", ["CREATE_IN_PROGRESS", "CREATE_COMPLETE"])
def test_repeated_create_returns_202_with_existing_stack_without_creating_again(
    aws_client,
    status,
) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    for _ in range(2):
        stub.identity()
        stub.stack(target, status=status)
        stub.events(target)

    responses = [
        client.post(deployment_url(target), json={"confirm_costs": True}) for _ in range(2)
    ]

    assert [response.status_code for response in responses] == [202, 202]
    assert responses[0].json() == responses[1].json()
    assert responses[0].json()["status"] == status
    assert responses[0].json()["stack_id"] == stack_id(target)


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_foreign_stack_returns_409_before_events_or_mutation(aws_client, method) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    stub.identity()
    stub.stack(
        target,
        Tags=[
            {"Key": "Application", "Value": "SECI-TI"},
            {"Key": "CaseId", "Value": "f" * 32},
            {"Key": "Architecture", "Value": target.architecture.value},
        ],
    )

    response = deployment_request(client, method, deployment_url(target))

    assert response.status_code == 409
    assert "no pertenece" in response.json()["detail"]


def test_delete_without_request_body_returns_202_and_deletes_by_verified_arn(aws_client) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    stub.identity()
    stub.stack(target)
    stub.events(target)
    stub.cf_stub.add_response(
        "delete_stack",
        {},
        {"StackName": stack_id(target), "ClientRequestToken": ANY},
    )

    response = client.delete(deployment_url(target))

    assert response.request.content == b""
    assert response.status_code == 202
    state = DeploymentState.model_validate(response.json())
    assert state.status == "DELETE_IN_PROGRESS"
    assert state.case_id == target.case_id
    assert state.stack_id == stack_id(target)
    assert state.outputs == {}


def test_delete_missing_stack_is_idempotent_and_returns_202(aws_client) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    for _ in range(2):
        stub.identity()
        stub.absent(target)

    responses = [client.delete(deployment_url(target)) for _ in range(2)]

    assert [response.status_code for response in responses] == [202, 202]
    assert responses[0].json() == responses[1].json()
    assert responses[0].json()["status"] == "NOT_DEPLOYED"
    assert responses[0].json()["stack_id"] is None


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_validation_errors_other_than_stack_absence_return_502(aws_client, method) -> None:
    client, stub, _ = aws_client()
    target = save_case(client)
    stub.identity()
    stub.cf_stub.add_client_error(
        "describe_stacks",
        service_error_code="ValidationError",
        service_message=PROVIDER_MESSAGE,
        expected_params={"StackName": stack_name(target)},
    )

    response = deployment_request(client, method, deployment_url(target))

    assert response.status_code == 502
    assert PROVIDER_MESSAGE not in response.text


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_sqlite_read_errors_return_503_without_contacting_aws(aws_client, method) -> None:
    client, stub, repository = aws_client()
    target = save_case(client)

    with patch.object(repository, "get", side_effect=CaseStorageError(SECRET_KEY)):
        response = deployment_request(client, method, deployment_url(target))

    assert response.status_code == 503
    assert response.json() == {"detail": "No fue posible consultar el caso guardado."}
    assert SECRET_KEY not in response.text
    stub.session_factory.assert_not_called()
