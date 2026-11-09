import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.ai.base import AIExtractionError
from app.persistence.repository import CaseStorageError
from app.schemas.architecture_advice import GenerateAdviceRequest, SavedArchitectureAdvice
from app.services.architecture_advice_service import (
    AdviceCaseNotFoundError,
    ArchitectureAdviceService,
)

router = APIRouter(prefix="/api/cases", tags=["architecture-advice"])
logger = logging.getLogger(__name__)


def get_advice_service(request: Request) -> ArchitectureAdviceService:
    return request.app.state.architecture_advice_service


@router.post("/{case_id}/advice", response_model=SavedArchitectureAdvice)
def generate_advice(
    case_id: str,
    payload: GenerateAdviceRequest,
    service: ArchitectureAdviceService = Depends(get_advice_service),
) -> SavedArchitectureAdvice:
    try:
        return service.generate(case_id, regenerate=payload.regenerate)
    except AdviceCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AIExtractionError as exc:
        logger.warning("Architecture advice failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="No fue posible generar las recomendaciones ampliadas. "
            "El caso y su recomendacion A/B/C siguen disponibles. Intenta nuevamente.",
        ) from exc
    except CaseStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail="No fue posible guardar o consultar el informe de recomendaciones.",
        ) from exc
