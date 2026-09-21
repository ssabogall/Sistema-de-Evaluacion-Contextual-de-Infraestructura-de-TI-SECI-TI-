import pytest
from fastapi.testclient import TestClient

from app.ai.base import AIRequirementExtractor
from app.config import Settings
from app.main import create_app
from tests.helpers import StaticExtractor


@pytest.fixture
def client_factory():
    def create(extractor: AIRequirementExtractor | None = None) -> TestClient:
        app = create_app(
            extractor=extractor or StaticExtractor(),
            settings=Settings(frontend_origins="http://localhost:5173"),
        )
        return TestClient(app)

    return create
