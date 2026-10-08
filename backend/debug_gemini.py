"""Script de diagnostico temporal -- NO es parte del sistema, es solo para
ver exactamente que esta devolviendo Gemini y por que falla la validacion.
Borralo cuando terminemos de diagnosticar (no debe quedar commiteado).

Uso: desde la raiz del repo, con el venv activado:
    python backend/debug_gemini.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai.base import AIExtractionError
from app.ai.gemini_extractor import GeminiRequirementExtractor
from app.config import get_settings

settings = get_settings()
api_key = settings.ai_api_key.get_secret_value() if settings.ai_api_key else None
model = settings.ai_model

print(f"Usando modelo: {model!r}")
print(f"API key leida (primeros 10 chars): {api_key[:10]!r} ... (len={len(api_key) if api_key else 0})")
print("-" * 60)

# Usamos la clase real, no una llamada hecha a mano -- asi el diagnostico
# prueba exactamente el mismo camino que recorre la app cuando el frontend
# pega a /api/business-cases/analyze.
extractor = GeminiRequirementExtractor(
    api_key=api_key,
    model=model,
    timeout_seconds=settings.ai_timeout_seconds,
)

business_case = (
    "Somos una tienda en linea pequena de ropa. Nuestro presupuesto es "
    "limitado. El trafico es estable, pero cada diciembre por Black "
    "Friday y Navidad las visitas se multiplican y lo sabemos con "
    "anticipacion porque lo planeamos cada ano. Si la pagina se cae un "
    "par de horas no es grave, pero si se cae varios dias perderiamos "
    "ventas importantes."
)

try:
    result = extractor.extract_requirements(business_case)
    print("EXTRACCION OK:")
    print(result.model_dump_json(indent=2))
except AIExtractionError as e:
    print(f"FALLO: {type(e).__name__}: {e}")
    print("Causa original (lo que el log de uvicorn no muestra):")
    print(repr(e.__cause__))
