from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai.base import (
    AIConfigurationError,
    AIProviderError,
    AIResponseValidationError,
)
from app.ai.openai_extractor import OpenAIRequirementExtractor
from app.ai.prompts.business_case_extractor import BUSINESS_CASE_EXTRACTOR_PROMPT
from app.schemas.business_case import BusinessCaseAnalysis
from tests.helpers import analysis_payload


def test_missing_api_key_is_controlled() -> None:
    extractor = OpenAIRequirementExtractor(api_key=None, model="test-model")

    with pytest.raises(AIConfigurationError):
        extractor.extract_requirements("Caso de negocio suficientemente largo.")


def test_empty_provider_response_is_controlled() -> None:
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=None)
    extractor = OpenAIRequirementExtractor("test-key", "test-model", client=client)

    with pytest.raises(AIResponseValidationError):
        extractor.extract_requirements("Caso de negocio suficientemente largo.")


def test_invalid_provider_schema_is_controlled() -> None:
    payload = analysis_payload()
    payload["requirements"]["available_budget"]["value"] = "unlimited"
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=payload)
    extractor = OpenAIRequirementExtractor("test-key", "test-model", client=client)

    with pytest.raises(AIResponseValidationError):
        extractor.extract_requirements("Caso de negocio suficientemente largo.")


def test_unexpected_provider_error_is_wrapped() -> None:
    client = Mock()
    client.responses.parse.side_effect = RuntimeError("provider down")
    extractor = OpenAIRequirementExtractor("test-key", "test-model", client=client)

    with pytest.raises(AIProviderError):
        extractor.extract_requirements("Caso de negocio suficientemente largo.")


def test_structured_output_call_uses_central_prompt_and_preserves_input() -> None:
    parsed = BusinessCaseAnalysis.model_validate(analysis_payload("texto alterado"))
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
    extractor = OpenAIRequirementExtractor("test-key", "test-model", client=client)
    original = "Texto original del caso de negocio con detalles suficientes."

    analysis = extractor.extract_requirements(original)

    assert analysis.business_case == original
    call = client.responses.parse.call_args.kwargs
    assert call["text_format"] is BusinessCaseAnalysis
    assert call["input"][0]["content"] == BUSINESS_CASE_EXTRACTOR_PROMPT
    assert "no eliges\narquitecturas" in BUSINESS_CASE_EXTRACTOR_PROMPT
    assert "servicios AWS" in BUSINESS_CASE_EXTRACTOR_PROMPT
