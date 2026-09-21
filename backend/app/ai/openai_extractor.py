from json import JSONDecodeError
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import ValidationError

from app.ai.base import (
    AIConfigurationError,
    AIProviderError,
    AIRequirementExtractor,
    AIResponseValidationError,
)
from app.ai.prompts.business_case_extractor import BUSINESS_CASE_EXTRACTOR_PROMPT
from app.schemas.business_case import BusinessCaseAnalysis


class OpenAIRequirementExtractor(AIRequirementExtractor):
    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        timeout_seconds: float = 30.0,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def extract_requirements(self, business_case: str) -> BusinessCaseAnalysis:
        if not self._api_key:
            raise AIConfigurationError("AI_API_KEY is not configured")
        if not self._model:
            raise AIConfigurationError("AI_MODEL is not configured")

        client = self._client or OpenAI(
            api_key=self._api_key,
            timeout=self._timeout_seconds,
        )

        try:
            response = client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": BUSINESS_CASE_EXTRACTOR_PROMPT},
                    {"role": "user", "content": business_case},
                ],
                text_format=BusinessCaseAnalysis,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise AIResponseValidationError("The provider returned no parsed output")

            analysis = BusinessCaseAnalysis.model_validate(parsed)
            payload = analysis.model_dump(mode="python")
            payload["business_case"] = business_case
            payload["requires_user_confirmation"] = True
            return BusinessCaseAnalysis.model_validate(payload)
        except AIResponseValidationError:
            raise
        except APITimeoutError as exc:
            raise AIProviderError("The AI provider timed out") from exc
        except (APIConnectionError, APIStatusError) as exc:
            raise AIProviderError("The AI provider request failed") from exc
        except (ValidationError, JSONDecodeError, TypeError, ValueError) as exc:
            raise AIResponseValidationError("The AI response failed schema validation") from exc
        except Exception as exc:
            raise AIProviderError("Unexpected AI provider failure") from exc
