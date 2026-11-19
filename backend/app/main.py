from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.architecture_advisor import (
    ArchitectureAdvisor,
    GeminiArchitectureAdvisor,
    OpenAIArchitectureAdvisor,
)
from app.ai.base import AIRequirementExtractor
from app.ai.gemini_extractor import GeminiRequirementExtractor
from app.ai.openai_extractor import OpenAIRequirementExtractor
from app.api.architecture_advice import router as advice_router
from app.api.aws import router as aws_router
from app.api.business_cases import router as business_cases_router
from app.api.cases import router as cases_router
from app.aws.cloudformation import AwsGateway, CloudFormationGateway
from app.config import Settings, get_settings
from app.persistence.repository import CaseRepository
from app.persistence.sqlite_repository import SqliteCaseRepository
from app.services.architecture_advice_service import ArchitectureAdviceService
from app.services.business_case_service import BusinessCaseService
from app.services.case_service import CaseService
from app.services.deployment_service import DeploymentService


def create_app(
    extractor: AIRequirementExtractor | None = None,
    settings: Settings | None = None,
    repository: CaseRepository | None = None,
    aws_gateway: AwsGateway | None = None,
    advisor: ArchitectureAdvisor | None = None,
) -> FastAPI:
    current_settings = settings or get_settings()
    api_key = (
        current_settings.ai_api_key.get_secret_value() if current_settings.ai_api_key else None
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
        description="Business analysis, architecture advice and AWS demonstration deployments.",
    )
    application.state.business_case_service = BusinessCaseService(current_extractor)
    current_repository = repository or SqliteCaseRepository(current_settings.database_path)
    application.state.case_service = CaseService(current_repository)
    advisor_type = (
        GeminiArchitectureAdvisor
        if current_settings.ai_provider == "gemini"
        else OpenAIArchitectureAdvisor
    )
    current_advisor = (
        advisor
        if advisor is not None
        else advisor_type(
            api_key=api_key,
            model=current_settings.ai_model,
            timeout_seconds=current_settings.ai_timeout_seconds,
        )
    )
    application.state.architecture_advice_service = ArchitectureAdviceService(
        current_repository,
        current_advisor,
        current_settings.ai_provider,
        current_settings.ai_model,
    )
    application.state.deployment_service = DeploymentService(
        application.state.case_service,
        aws_gateway if aws_gateway is not None else CloudFormationGateway(current_settings),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(business_cases_router)
    application.include_router(cases_router)
    application.include_router(aws_router)
    application.include_router(advice_router)

    @application.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
