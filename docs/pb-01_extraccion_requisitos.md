# PB-01: Extracción y confirmación de requisitos

## Alcance

PB-01 convierte un caso de negocio escrito en lenguaje natural en seis variables
canónicas validadas. El resultado siempre pasa por revisión y confirmación humana.
Este módulo no calcula puntajes, no asigna pesos y no selecciona arquitecturas.

## Flujo

1. El frontend envía la descripción a `POST /api/business-cases/analyze`.
2. `BusinessCaseService` delega la interpretación en `AIRequirementExtractor`.
3. `OpenAIRequirementExtractor` solicita una salida estructurada y la valida con
   `BusinessCaseAnalysis`.
4. La interfaz presenta valor, estado y evidencia de cada requisito.
5. El usuario puede modificar valores, completar ausencias y resolver conflictos.
6. `POST /api/business-cases/confirm` devuelve un objeto con estado `confirmed`.

## Decisiones

- FastAPI y Pydantic mantienen el contrato cerrado y facilitan explicar y probar
  la frontera entre IA y aplicación.
- El SDK de OpenAI solo aparece en `app/ai/openai_extractor.py`; el resto del
  sistema depende de `AIRequirementExtractor`.
- No hay umbrales automáticos para montos, usuarios, concurrencia o solicitudes.
  Los números explícitos se conservan en `additional_context`.
- `unknown` requiere ausencia de evidencia. `conflict` requiere valor `unknown` y
  al menos dos fragmentos contradictorios.
- El texto original se restaura en el backend incluso si el proveedor devuelve
  una copia modificada.
- Los modelos prohíben campos adicionales, por lo que una selección de
  arquitectura no puede entrar en el contrato de PB-01.

## Frontera con PB-02

PB-02 podrá consumir `requirements` del objeto confirmado. La implementación de
SAW, rankings, pesos y selección A/B/C permanece fuera de este módulo.
