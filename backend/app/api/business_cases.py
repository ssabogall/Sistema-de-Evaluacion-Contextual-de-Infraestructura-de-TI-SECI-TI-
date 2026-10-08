import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.ai.base import AIExtractionError
from app.schemas.business_case import (
    AnalyzeBusinessCaseRequest,
    BusinessCaseAnalysis,
    BusinessCaseConfirmationRequest,
    ConfirmedBusinessCase,
)
from app.services.business_case_service import BusinessCaseService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/business-cases", tags=["business-cases"])
PUBLIC_ANALYSIS_ERROR = "No fue posible analizar el caso en este momento. Intenta nuevamente."


def get_business_case_service(request: Request) -> BusinessCaseService:
    return request.app.state.business_case_service


@router.post("/analyze", response_model=BusinessCaseAnalysis)
def analyze_business_case(
    payload: AnalyzeBusinessCaseRequest,
    service: BusinessCaseService = Depends(get_business_case_service),
) -> BusinessCaseAnalysis:
    try:
        return service.analyze(payload.description)
    except AIExtractionError as exc:
        logger.warning("Business case analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PUBLIC_ANALYSIS_ERROR,
        ) from exc


@router.post("/confirm", response_model=ConfirmedBusinessCase)
def confirm_business_case(
    payload: BusinessCaseConfirmationRequest,
    service: BusinessCaseService = Depends(get_business_case_service),
) -> ConfirmedBusinessCase:
    return service.confirm(payload)
