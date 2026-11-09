"""Structured architecture advice, independent of the catalog engine and AWS."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from json import JSONDecodeError
from math import ceil, isfinite
from typing import Any

from google import genai
from google.genai import types as genai_types
from httpx import TimeoutException
from openai import APITimeoutError, OpenAI
from pydantic import ValidationError

from app.ai.base import AIConfigurationError, AIProviderError, AIResponseValidationError
from app.ai.prompts.architecture_advisor import ARCHITECTURE_ADVISOR_PROMPT
from app.schemas.architecture_advice import AdviceInput, ArchitectureAdvice
from app.schemas.project_context import ProjectScenario


class ArchitectureAdvisor(ABC):
    @abstractmethod
    def recommend(self, payload: AdviceInput) -> ArchitectureAdvice:
        """Advise on confirmed context without modifying it or executing changes."""


def _check_configuration(api_key: str | None, model: str | None, timeout: float) -> None:
    if not isinstance(api_key, str) or not api_key.strip():
        raise AIConfigurationError("AI_API_KEY is not configured")
    if not isinstance(model, str) or not model.strip():
        raise AIConfigurationError("AI_MODEL is not configured")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not isfinite(timeout)
        or timeout <= 0
    ):
        raise AIConfigurationError("The AI timeout must be finite and positive")


@contextmanager
def _provider_client(injected: Any | None, factory: Callable[[], Any]) -> Iterator[Any]:
    """Own only created clients and hide provider details, including exception chains."""
    client = None
    try:
        client = injected if injected is not None else factory()
        try:
            yield client
        except BaseException:
            if injected is None:
                # Cleanup must not mask the original request or validation failure.
                with suppress(Exception):
                    client.close()
            raise
        else:
            if injected is None:
                client.close()
    except (AIProviderError, AIResponseValidationError):
        raise
    except (APITimeoutError, TimeoutException, TimeoutError):
        raise AIProviderError("The AI provider timed out") from None
    except (ValidationError, JSONDecodeError, TypeError, ValueError, AttributeError):
        raise AIResponseValidationError("The AI response failed schema validation") from None
    except Exception:
        raise AIProviderError("The AI provider request failed") from None


def _field(value: Any, name: str) -> Any:
    """Read SDK metadata or fake metadata; scalar envelopes are malformed."""
    if isinstance(value, dict):
        return value.get(name)
    if value is None or isinstance(value, (str, bytes, int, float, bool, list, tuple)):
        raise ValueError("Malformed provider metadata")
    return getattr(value, name, None)


def _check_openai_metadata(response: Any) -> None:
    status = _field(response, "status")
    if status is not None and status != "completed":
        raise AIResponseValidationError("The AI response is not complete")
    if _field(response, "error") is not None or _field(response, "incomplete_details") is not None:
        raise AIResponseValidationError("The AI response is not complete")
    output = _field(response, "output")
    if output is None:
        return
    if not isinstance(output, list) or not output:
        raise AIResponseValidationError("The AI response has invalid output metadata")
    has_message = False
    for item in output:
        kind = _field(item, "type")
        if kind == "reasoning":
            continue
        if kind != "message" or _field(item, "status") not in (None, "completed"):
            raise AIResponseValidationError("The AI response has invalid output metadata")
        content = _field(item, "content")
        if not isinstance(content, list) or not content:
            raise AIResponseValidationError("The AI response has invalid content metadata")
        if any(_field(part, "type") != "output_text" for part in content):
            raise AIResponseValidationError("The AI response did not contain structured advice")
        has_message = True
    if not has_message:
        raise AIResponseValidationError("The AI response did not contain an advice message")


def _check_gemini_metadata(response: Any) -> None:
    feedback = _field(response, "prompt_feedback")
    if feedback is not None:
        reason = _field(feedback, "block_reason")
        if reason not in (None, "BLOCKED_REASON_UNSPECIFIED"):
            raise AIResponseValidationError("The AI provider blocked the response")
    candidates = _field(response, "candidates")
    if candidates is None:
        return
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise AIResponseValidationError("The AI response has invalid candidate metadata")
    if _field(candidates[0], "finish_reason") != "STOP":
        raise AIResponseValidationError("The AI response is not complete")


def _check_scenario(advice: ArchitectureAdvice, payload: AdviceInput) -> ArchitectureAdvice:
    assessment = advice.current_architecture_assessment
    if payload.confirmed.project_context.scenario == ProjectScenario.EXISTING:
        if assessment is None:
            raise AIResponseValidationError("Existing platforms require an architecture assessment")
    elif assessment is not None:
        raise AIResponseValidationError("New platforms must not include an architecture assessment")
    return advice


def _gemini_advice_schema() -> dict[str, Any]:
    """Omit Gemini's incompatible generation bounds; Pydantic still enforces them."""

    def without_bounds(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                key: without_bounds(value)
                for key, value in node.items()
                if key not in ("minLength", "maxLength", "minItems", "maxItems")
            }
        if isinstance(node, list):
            return [without_bounds(value) for value in node]
        return node

    return without_bounds(ArchitectureAdvice.model_json_schema())


class OpenAIArchitectureAdvisor(ArchitectureAdvisor):
    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        timeout_seconds: float = 30,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def recommend(self, payload: AdviceInput) -> ArchitectureAdvice:
        _check_configuration(self._api_key, self._model, self._timeout_seconds)
        with _provider_client(
            self._client,
            lambda: OpenAI(api_key=self._api_key, timeout=self._timeout_seconds),
        ) as client:
            response = client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": ARCHITECTURE_ADVISOR_PROMPT},
                    {"role": "user", "content": payload.model_dump_json()},
                ],
                text_format=ArchitectureAdvice,
                timeout=self._timeout_seconds,
                store=False,
            )
            _check_openai_metadata(response)
            parsed = _field(response, "output_parsed")
            if parsed is None:
                raise AIResponseValidationError("The AI provider returned no parsed advice")
            # Revalidate instances too: SDKs/fakes can return constructed or modified models.
            if isinstance(parsed, ArchitectureAdvice):
                parsed = parsed.model_dump(mode="python", warnings=False)
            advice = ArchitectureAdvice.model_validate(parsed)
            return _check_scenario(advice, payload)


class GeminiArchitectureAdvisor(ArchitectureAdvisor):
    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        timeout_seconds: float = 30,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def recommend(self, payload: AdviceInput) -> ArchitectureAdvice:
        _check_configuration(self._api_key, self._model, self._timeout_seconds)
        # HttpOptions uses integer milliseconds, including for an injected client's request.
        http_options = genai_types.HttpOptions(timeout=ceil(self._timeout_seconds * 1000))
        with _provider_client(
            self._client,
            lambda: genai.Client(api_key=self._api_key, http_options=http_options),
        ) as client:
            response = client.models.generate_content(
                model=self._model,
                contents=payload.model_dump_json(),
                config=genai_types.GenerateContentConfig(
                    system_instruction=ARCHITECTURE_ADVISOR_PROMPT,
                    response_mime_type="application/json",
                    # Preserve object restrictions, references and enums; validate bounds below.
                    response_json_schema=_gemini_advice_schema(),
                    http_options=http_options,
                ),
            )
            _check_gemini_metadata(response)
            text = _field(response, "text")
            if not isinstance(text, str) or not text.strip():
                raise AIResponseValidationError("The AI provider returned no advice text")
            advice = ArchitectureAdvice.model_validate_json(text)
            return _check_scenario(advice, payload)
