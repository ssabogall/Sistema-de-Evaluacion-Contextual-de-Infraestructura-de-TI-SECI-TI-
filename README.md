# SECI-TI

Sistema de Evaluación Contextual de Infraestructura de TI. Esta versión implementa
exclusivamente **PB-01**: caso de negocio → extracción con IA → requisitos
estructurados → revisión → corrección → confirmación humana.

No incluye puntajes, SAW, pesos, selección de Arquitectura A/B/C, AWS, despliegue
ni validación experimental.

## Estructura

```text
backend/   API FastAPI, schemas Pydantic, servicio y proveedor de IA
frontend/  Aplicación React + TypeScript + Vite
docs/      Requisitos, decisiones del proyecto y alcance de PB-01
```

El detalle de diseño de esta fase está en
[`docs/pb-01_extraccion_requisitos.md`](docs/pb-01_extraccion_requisitos.md).

## Configuración

1. Copia `.env.example` como `.env` en la raíz.
2. Define `AI_API_KEY` con una credencial válida.
3. Define `AI_MODEL` con un modelo disponible en tu proyecto que soporte
   Structured Outputs.

La clave solo se carga en el backend. No se envía al navegador ni se registra en
logs. La implementación usa el patrón tipado de Structured Outputs documentado
por OpenAI: https://developers.openai.com/api/docs/guides/structured-outputs

## Backend

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\backend[dev]"
uvicorn app.main:app --app-dir backend --reload
```

La API queda en `http://localhost:8000` y su documentación interactiva en
`http://localhost:8000/docs`.

## Frontend

En otra terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

La interfaz queda en `http://localhost:5173`. Vite reenvía las solicitudes `/api`
al backend local.

## Pruebas

```powershell
python -m pytest backend/tests
Set-Location frontend
npm test
npm run build
```

Las pruebas normales usan extractores falsos y no consumen tokens. Para ejecutar
la validación opcional contra el proveedor real:

```powershell
python -m pytest backend/tests/test_openai_integration.py -m integration
```

Esa prueba solo se habilita cuando `AI_API_KEY` y `AI_MODEL` están configurados.

## API

Analizar:

```http
POST /api/business-cases/analyze
Content-Type: application/json

{
  "description": "Necesitamos una aplicación interna con tráfico estable y presupuesto limitado."
}
```

Confirmar después de la revisión:

```http
POST /api/business-cases/confirm
Content-Type: application/json

{
  "business_case": "...",
  "requirements": { "...": "seis variables canónicas" },
  "additional_context": {}
}
```

La respuesta final contiene `status: "confirmed"`, el caso original, los seis
requisitos y el contexto adicional.
