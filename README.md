# SECI-TI

Sistema de Evaluación Contextual de Infraestructura de TI. Esta versión implementa
el flujo caso de negocio y arquitectura actual → extracción con IA → revisión y
confirmación humana → recomendación determinística A/B/C → caso guardado →
recomendaciones ampliadas con IA y despliegue de demostración en AWS.

El motor usa puntajes ponderados y prioridades confirmadas. Los casos se guardan
en SQLite. La conexión AWS y el despliegue con CloudFormation son opcionales;
las pruebas de carga con k6 y la validación experimental con CloudWatch siguen
pendientes.

## Plataformas nuevas y existentes

El formulario permite seleccionar una plataforma nueva o describir una existente.
En el segundo caso se guarda también la arquitectura actual: componentes, servicios,
datos, conexiones y problemas expresados por el usuario. La extracción conserva
ese texto sin tratar las capacidades actuales como requisitos deseados.

El detalle del caso mantiene la recomendación A/B/C y añade un informe de IA con
mejoras priorizadas, alternativas fuera del catálogo, pasos siguientes, supuestos
y preguntas pendientes. El informe se solicita con **Generar recomendaciones**;
abrir o guardar un caso no genera este informe ni consume tokens adicionales por él.
Una vez generado se guarda en SQLite y sólo se vuelve a llamar a la IA al regenerarlo.

Las sugerencias se basan en la descripción y los requisitos confirmados. No se
inspecciona la plataforma real ni se ejecutan las sugerencias. El botón de despliegue
sigue utilizando las plantillas A/B/C y la misma aplicación de demostración.
Los casos anteriores continúan disponibles sin tener que volver a analizarlos.

El contrato y las decisiones están en
[`docs/pb-04_contexto_y_recomendaciones.md`](docs/pb-04_contexto_y_recomendaciones.md).

## Estructura

```text
backend/   API FastAPI, schemas Pydantic, servicio y proveedor de IA
frontend/  Aplicación React + TypeScript + Vite
docs/      Requisitos, decisiones del proyecto y alcance de PB-01
infrastructure/  Plantillas CloudFormation del catálogo A/B/C
```

El detalle de diseño de esta fase está en
[`docs/pb-01_extraccion_requisitos.md`](docs/pb-01_extraccion_requisitos.md).

## Configuración

1. Copia `.env.example` como `.env` en la raíz.
2. Define `AI_PROVIDER` (`openai` o `gemini`) y `AI_API_KEY` con una credencial válida.
3. Define `AI_MODEL` con un modelo disponible en tu proyecto que soporte
   salidas estructuradas.

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

## Conexion y despliegue AWS

El proyecto inicia sin credenciales AWS. Para conectar un Learner Lab o un perfil
AWS propio, sigue [la configuracion AWS](docs/pb-03_conexion_aws.md).

En el detalle de un caso guardado puedes verificar cuenta y region, desplegar
la arquitectura recomendada, consultar sus eventos y eliminar el stack al terminar.
`AWS_ENABLED=true` habilita la conexion; `AWS_ALLOW_DEPLOYMENTS=true` permite crear
y eliminar recursos. Cada despliegue pide confirmacion en la interfaz porque los
recursos de AWS generan cargos. Las claves permanecen en el backend.

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

Las pruebas AWS usan respuestas simuladas con `botocore.stub.Stubber`: no requieren
credenciales ni crean infraestructura. Valida tambien las plantillas con:

```powershell
cfn-lint infrastructure/architecture-a/template.yaml infrastructure/architecture-b/template.yaml infrastructure/architecture-c/template.yaml
```

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

Para una plataforma existente, `POST /api/business-cases/analyze` también acepta:

```json
{
  "description": "Nuestro portal recibe picos de visitas y debe seguir disponible durante las ventas.",
  "project_context": {
    "scenario": "existing",
    "current_architecture": "Una VM ejecuta Nginx, la aplicación y PostgreSQL. Los respaldos son manuales y los reportes lentos durante las ventas."
  }
}
```

`project_context` se conserva al confirmar y guardar el caso. Para el informe ampliado:

```http
POST /api/cases/{id}/advice
Content-Type: application/json

{"regenerate": false}
```

La respuesta contiene `generated_at`, `provider`, `model` y `content`. Si ya existe
un informe, se devuelve el guardado. `{"regenerate": true}` solicita una nueva
respuesta al proveedor y reemplaza el informe sólo después de validar y guardar
el resultado correctamente.
