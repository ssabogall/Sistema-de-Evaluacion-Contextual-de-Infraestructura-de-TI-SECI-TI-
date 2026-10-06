from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.base import AIRequirementExtractor
from app.ai.gemini_extractor import GeminiRequirementExtractor
from app.ai.openai_extractor import OpenAIRequirementExtractor
from app.api.business_cases import router as business_cases_router
from app.config import Settings, get_settings
from app.services.business_case_service import BusinessCaseService


def create_app(
    extractor: AIRequirementExtractor | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    current_settings = settings or get_settings()
    api_key = (
        current_settings.ai_api_key.get_secret_value()
        if current_settings.ai_api_key
        else None
    )
    if extractor is not None:
        current_extractor = extractor
    elif current_settings.ai_provider == "gemini":
        current_extractor = GeminiRequirementExtractor(
            api_key=api_key,
            model=current_settings.ai_model,
            timeout_seconds=current_settings.ai_timeout_seconds,
        )
    else:
        current_extractor = OpenAIRequirementExtractor(
            api_key=api_key,
            model=current_settings.ai_model,
            timeout_seconds=current_settings.ai_timeout_seconds,
        )

    application = FastAPI(
        title="SECI-TI API",
        version="0.1.0",
        description="PB-01: extraction and human confirmation of business requirements.",
    )
    application.state.business_case_service = BusinessCaseService(current_extractor)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(business_cases_router)

    @application.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
