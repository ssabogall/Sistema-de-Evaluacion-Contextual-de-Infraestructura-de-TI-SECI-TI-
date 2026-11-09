from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.base import AIRequirementExtractor
from app.config import Settings
from app.persistence.repository import CaseRepository
from app.persistence.sqlite_repository import SqliteCaseRepository
from tests.helpers import StaticExtractor

if TYPE_CHECKING:
    from app.ai.architecture_advisor import ArchitectureAdvisor

# main creates a module-level app; importing it must not read local secret files.
with patch.dict(Settings.model_config, env_file=None):
    from app.main import create_app


@pytest.fixture
def client_factory(tmp_path):
    default_settings = Settings(
        _env_file=None,
        frontend_origins="http://localhost:5173",
        ai_provider="openai",
        ai_api_key=None,
        ai_model=None,
        aws_enabled=False,
        aws_allow_deployments=False,
    )

    def create(
        extractor: AIRequirementExtractor | None = None,
        repository: CaseRepository | None = None,
        advisor: "ArchitectureAdvisor | None" = None,
        settings: Settings | None = None,
    ) -> TestClient:
        app = create_app(
            extractor=extractor or StaticExtractor(),
            repository=repository or SqliteCaseRepository(tmp_path / "cases.sqlite3"),
            settings=settings or default_settings,
            advisor=advisor,
        )
        return TestClient(app)

    return create
