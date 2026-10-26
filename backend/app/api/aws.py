import logging
from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.aws.errors import AwsError
from app.persistence.repository import CaseStorageError
from app.schemas.deployment import AwsConnection, CreateDeploymentRequest, DeploymentState
from app.services.deployment_service import DeploymentService

router = APIRouter(prefix="/api", tags=["aws"])
logger = logging.getLogger(__name__)
T = TypeVar("T")


def get_deployment_service(request: Request) -> DeploymentService:
    return request.app.state.deployment_service


def _execute(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except AwsError as exc:
        logger.warning("AWS operation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except CaseStorageError as exc:
        raise HTTPException(
            status_code=503, detail="No fue posible consultar el caso guardado."
        ) from exc


@router.get("/aws/connection", response_model=AwsConnection)
def connection(service: DeploymentService = Depends(get_deployment_service)) -> AwsConnection:
    return _execute(service.connection)


@router.get("/cases/{case_id}/deployment", response_model=DeploymentState)
def deployment_status(
    case_id: str,
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentState:
    return _execute(lambda: service.get(case_id))


@router.post(
    "/cases/{case_id}/deployment",
    response_model=DeploymentState,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_deployment(
    case_id: str,
    payload: CreateDeploymentRequest,
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentState:
    return _execute(lambda: service.create(case_id))


@router.delete(
    "/cases/{case_id}/deployment",
    response_model=DeploymentState,
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_deployment(
    case_id: str,
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentState:
    return _execute(lambda: service.delete(case_id))
