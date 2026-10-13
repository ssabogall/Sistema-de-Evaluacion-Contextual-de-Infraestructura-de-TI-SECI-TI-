import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.business_cases import get_business_case_service
from app.persistence.models import CaseRecord, CaseSummary
from app.persistence.repository import CaseStorageError
from app.schemas.business_case import BusinessCaseConfirmationRequest
from app.services.business_case_service import BusinessCaseService
from app.services.case_service import CaseService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cases", tags=["cases"])
PUBLIC_STORAGE_ERROR = "No fue posible guardar o consultar los casos en este momento."
CASE_NOT_FOUND = "No encontramos ese caso."


def get_case_service(request: Request) -> CaseService:
    return request.app.state.case_service


@router.post("", response_model=CaseRecord, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: BusinessCaseConfirmationRequest,
    business_case_service: BusinessCaseService = Depends(get_business_case_service),
    case_service: CaseService = Depends(get_case_service),
) -> CaseRecord:
    """Confirma los requisitos, calcula la recomendacion del motor y guarda el caso."""
    confirmed = business_case_service.confirm(payload)
    try:
        return case_service.create(confirmed)
    except CaseStorageError as exc:
        logger.error("Could not store case: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=PUBLIC_STORAGE_ERROR
        ) from exc


@router.get("", response_model=list[CaseSummary])
def list_cases(
    limit: int = Query(default=50, ge=1, le=200),
    case_service: CaseService = Depends(get_case_service),
) -> list[CaseSummary]:
    try:
        return case_service.list_recent(limit)
    except CaseStorageError as exc:
        logger.error("Could not list cases: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=PUBLIC_STORAGE_ERROR
        ) from exc


@router.get("/{case_id}", response_model=CaseRecord)
def get_case(
    case_id: str,
    case_service: CaseService = Depends(get_case_service),
) -> CaseRecord:
    try:
        record = case_service.get(case_id)
    except CaseStorageError as exc:
        logger.error("Could not read case %s: %s", case_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=PUBLIC_STORAGE_ERROR
        ) from exc
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CASE_NOT_FOUND)
    return record
