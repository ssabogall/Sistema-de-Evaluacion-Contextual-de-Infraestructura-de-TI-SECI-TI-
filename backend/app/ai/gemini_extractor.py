from json import JSONDecodeError

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.base import (
    AIConfigurationError,
    AIProviderError,
    AIRequirementExtractor,
    AIResponseValidationError,
)
from app.ai.prompts.business_case_extractor import BUSINESS_CASE_EXTRACTOR_PROMPT
from app.schemas.business_case import (
    AdditionalContext,
    BusinessCaseAnalysis,
    RequirementKey,
    Requirements,
)


class _GeminiAnalysisSchema(BaseModel):
    """BusinessCaseAnalysis sin `requires_user_confirmation`.

    El traductor de esquemas de Gemini rechaza `Literal` con valores que no
    son string (`Literal[True]` revienta con
    "ValueError: Literal values must be strings." dentro del SDK). Ese campo
    siempre se fuerza a True despues de recibir la respuesta (ver mas abajo,
    igual que en openai_extractor.py), asi que la solucion es no pedirselo
    al modelo, en vez de aflojar el esquema compartido de business_case.py
    para los dos proveedores.
    """

    model_config = ConfigDict(extra="forbid")

    business_case: str = Field(min_length=1, max_length=20_000)
    requirements: Requirements
    additional_context: AdditionalContext = Field(default_factory=AdditionalContext)
    missing_requirements: list[RequirementKey] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _strip_additional_properties(node: object) -> object:
    """Elimina `additionalProperties` del JSON Schema que exporta Pydantic.

    Pydantic agrega esa clave automaticamente en cualquier modelo con
    `extra="forbid"` (Requirement, Requirements, AdditionalContext, y
    nuestro propio _GeminiAnalysisSchema, todos la tienen). Gemini no
    reconoce esa palabra clave del esquema de salida y rechaza la peticion
    completa con 400 INVALID_ARGUMENT si aparece en cualquier nivel
    anidado. Esto NO afecta la validacion real -- seguimos usando los
    modelos con extra="forbid" tal cual para validar lo que Gemini
    devuelve, solo limpiamos lo que le *pedimos* que genere.
    """
    if isinstance(node, dict):
        node.pop("additionalProperties", None)
        for value in node.values():
            _strip_additional_properties(value)
    elif isinstance(node, list):
        for item in node:
            _strip_additional_properties(item)
    return node


class GeminiRequirementExtractor(AIRequirementExtractor):
    """Same contract as OpenAIRequirementExtractor, backed by the Gemini API.

    Mirrors backend/app/ai/openai_extractor.py on purpose: the rest of the
    system (BusinessCaseService, the API layer) only knows about
    AIRequirementExtractor, so this class is the only place that needs to
    know Gemini exists.
    """

    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        timeout_seconds: float = 30.0,
        client: genai.Client | None = None,
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

        client = self._client or genai.Client(api_key=self._api_key)

        try:
            response = client.models.generate_content(
                model=self._model,
                contents=business_case,
                config=genai_types.GenerateContentConfig(
                    system_instruction=BUSINESS_CASE_EXTRACTOR_PROMPT,
                    response_mime_type="application/json",
                    # Pasamos un dict (no la clase Pydantic directamente)
                    # porque necesitamos limpiarlo primero con
                    # _strip_additional_properties. Como consecuencia,
                    # response.parsed ya no se autocompleta -- por eso mas
                    # abajo usamos response.text en su lugar.
                    response_schema=_strip_additional_properties(
                        _GeminiAnalysisSchema.model_json_schema()
                    ),
                    # DECISION PENDIENTE (equipo): el SDK de google-genai
                    # permite fijar un timeout via http_options, pero no
                    # confirmamos en que unidad (ms o s) ni en que version
                    # del SDK quedo asi. self._timeout_seconds existe y se
                    # recibe por configuracion, pero no se esta aplicando
                    # todavia aqui a proposito -- verifiquen la
                    # documentacion vigente de google-genai antes de
                    # cablear esto, para no fijar un valor equivocado en
                    # silencio.
                ),
            )
            if not response.text:
                raise AIResponseValidationError("The provider returned no parsed output")

            partial = _GeminiAnalysisSchema.model_validate_json(response.text)
            payload = partial.model_dump(mode="python")
            payload["business_case"] = business_case
            payload["requires_user_confirmation"] = True
            return BusinessCaseAnalysis.model_validate(payload)
        except AIResponseValidationError:
            raise
        except genai_errors.ClientError as exc:
            # 4xx de Gemini: incluye API key invalida/vencida, cuota del
            # free tier agotada, modelo inexistente, argumento invalido.
            # DECISION PENDIENTE (equipo): hoy todo 4xx cae como
            # AIProviderError generico, igual que el resto de fallas del
            # proveedor. Si quieren que una key mal configurada se vea
            # distinto de "el proveedor fallo" (por ejemplo para mostrar
            # un mensaje distinto en el frontend), aqui es donde tendrian
            # que inspeccionar exc y relanzar como AIConfigurationError en
            # los casos que correspondan -- no lo decidimos por ustedes.
            raise AIProviderError("The AI provider rejected the request") from exc
        except genai_errors.ServerError as exc:
            raise AIProviderError("The AI provider request failed") from exc
        except (ValidationError, JSONDecodeError, TypeError, ValueError) as exc:
            raise AIResponseValidationError("The AI response failed schema validation") from exc
        except Exception as exc:
            raise AIProviderError("Unexpected AI provider failure") from exc
