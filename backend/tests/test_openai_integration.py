import os

import pytest

from app.ai.openai_extractor import OpenAIRequirementExtractor
from tests.test_curated_cases import CURATED_CASES


HAS_AI_CONFIG = bool(os.getenv("AI_API_KEY") and os.getenv("AI_MODEL"))


@pytest.mark.integration
@pytest.mark.skipif(not HAS_AI_CONFIG, reason="AI_API_KEY and AI_MODEL are required")
@pytest.mark.parametrize("business_case,expected,_", CURATED_CASES)
def test_real_extractor_against_curated_cases(
    business_case: str,
    expected: dict,
    _: dict,
) -> None:
    extractor = OpenAIRequirementExtractor(
        api_key=os.environ["AI_API_KEY"],
        model=os.environ["AI_MODEL"],
    )

    analysis = extractor.extract_requirements(business_case)

    for key, expected_requirement in expected.items():
        actual = getattr(analysis.requirements, key)
        assert actual.value.value == expected_requirement["value"]
        assert actual.status.value == expected_requirement["status"]
