"""Script de diagnostico temporal -- NO es parte del sistema, es solo para
ver exactamente que esta devolviendo Gemini y por que falla la validacion.
Borralo cuando terminemos de diagnosticar (no debe quedar commiteado).

Uso: desde la raiz del repo, con el venv activado:
    python backend/debug_gemini.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from google import genai
from pydantic import ValidationError

from app.ai.prompts.business_case_extractor import BUSINESS_CASE_EXTRACTOR_PROMPT
from app.config import get_settings
from app.schemas.business_case import BusinessCaseAnalysis

settings = get_settings()
api_key = settings.ai_api_key.get_secret_value() if settings.ai_api_key else None
model = settings.ai_model

print(f"Usando modelo: {model!r}")
print(f"API key leida (primeros 10 chars): {api_key[:10]!r} ... (len={len(api_key) if api_key else 0})")
print("-" * 60)

client = genai.Client(api_key=api_key)

business_case = (
    "Somos una tienda en linea pequena de ropa. Nuestro presupuesto es "
    "limitado. El trafico es estable, pero cada diciembre por Black "
    "Friday y Navidad las visitas se multiplican y lo sabemos con "
    "anticipacion porque lo planeamos cada ano. Si la pagina se cae un "
    "par de horas no es grave, pero si se cae varios dias perderiamos "
    "ventas importantes."
)

response = client.models.generate_content(
    model=model,
    contents=business_case,
    config={
        "system_instruction": BUSINESS_CASE_EXTRACTOR_PROMPT,
        "response_mime_type": "application/json",
        "response_schema": BusinessCaseAnalysis,
    },
)

print("RESPONSE.TEXT (JSON crudo devuelto por Gemini):")
print(response.text)
print("-" * 60)

print("RESPONSE.PARSED (lo que el SDK logro parsear automaticamente):")
print(response.parsed)
print("-" * 60)

print("Intentando validar manualmente con BusinessCaseAnalysis.model_validate_json:")
try:
    result = BusinessCaseAnalysis.model_validate_json(response.text)
    print("VALIDACION OK:")
    print(result)
except ValidationError as e:
    print("VALIDACION FALLO -- este es el detalle real que el log de uvicorn no muestra:")
    print(e)
