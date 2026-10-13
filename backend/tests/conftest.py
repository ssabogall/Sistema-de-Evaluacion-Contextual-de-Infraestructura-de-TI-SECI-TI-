import pytest
from fastapi.testclient import TestClient

from app.ai.base import AIRequirementExtractor
from app.config import Settings
from app.main import create_app
from app.persistence.repository import CaseRepository
from app.persistence.sqlite_repository import SqliteCaseRepository
from tests.helpers import StaticExtractor


@pytest.fixture
def client_factory(tmp_path):
    def create(
        extractor: AIRequirementExtractor | None = None,
        repository: CaseRepository | None = None,
    ) -> TestClient:
        app = create_app(
            extractor=extractor or StaticExtractor(),
            repository=repository or SqliteCaseRepository(tmp_path / "cases.sqlite3"),
            settings=Settings(frontend_origins="http://localhost:5173"),
        )
        return TestClient(app)

    return create
