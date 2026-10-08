# Convenciones de código y flujo de trabajo — SECI-TI

Adaptado de referencias de otro proyecto (NestJS/TypeORM + Vue/Pinia), pero
**traducido al stack real de SECI-TI**: FastAPI + Pydantic en backend,
React + TypeScript en frontend. No se copian reglas especificas de un
framework que no usamos (decoradores de Nest, Single File Components de
Vue, Pinia). Donde el stack ya impone algo automaticamente (orden de
imports via `ruff`/ESLint, tipado via `strict: true`), no se repite aqui
como regla manual — revisen con `ruff check backend` y `npm run lint`.

## Reglas esenciales (backend)

- **Tipado explicito en toda funcion publica** (parametros y retorno). Ya
  es el patron en todo PB-01 (`ai/base.py`, `services/business_case_service.py`).
- **Routers delgados** (`app/api/*.py`): solo reciben el request, llaman al
  servicio correspondiente, devuelven la respuesta. Nada de logica de
  negocio ahi — ver `business_cases.py` como referencia de tamano correcto.
- **Los servicios son dueños de la logica de negocio** (`app/services/*.py`):
  reglas, validaciones, orquestacion entre capas.
- **Organizacion por dominio**, ya establecida — mantenerla al crear el
  motor de decision:
  - `app/ai/` — solo sabe hablar con proveedores de IA
  - `app/schemas/` — solo contratos de datos (Pydantic)
  - `app/services/` — orquestacion
  - `app/api/` — HTTP
  - Modulo nuevo para PB-02 (ej. `app/decision_engine/`): mismo criterio,
    una responsabilidad, no se mezcla con los anteriores
- **Contratos (DTOs) via Pydantic con `extra="forbid"`**, nunca estructuras
  sueltas (dict sin tipar) como entrada o salida de una funcion publica.
- **Errores con excepciones tipadas, no respuestas manuales**: el patron ya
  existe (`AIConfigurationError`/`AIProviderError`/`AIResponseValidationError`
  en `ai/base.py`) — si el motor de decision necesita sus propios tipos de
  error, seguir el mismo patron: jerarquia propia, capturada en la capa API
  y traducida a un codigo HTTP apropiado, nunca un `except Exception` que
  devuelva un dict armado a mano.
- **Revalidar siempre contra el modelo Pydantic estricto** cualquier dato
  que venga de una fuente externa (IA, request HTTP) antes de usarlo — ya
  es el patron en `gemini_extractor.py`/`openai_extractor.py`.
- **Prefijo de API consistente** (`/api/...`) para cualquier endpoint nuevo.
- **Variables de entorno**: todo en `.env`, documentado en `.env.example`,
  nunca hardcoded — ya es el patron existente (`AI_PROVIDER`, `FRONTEND_ORIGINS`).

### Imports (backend)

Orden: stdlib → terceros → internos (`app.*`), alfabetico dentro de cada
bloque. `ruff` (regla `I`, isort) ya lo verifica solo — no se revisa a mano.

### Capas (equivalencia con el documento de referencia NestJS)

| Referencia (Nest) | Aqui (FastAPI) |
|---|---|
| Controller | `app/api/*.py` (router) |
| Service | `app/services/*.py` |
| DTO | `app/schemas/*.py` (Pydantic) |
| Entity/Repository | No aplica — no hay base de datos en PB-01/PB-02. Si en algun punto el proyecto necesita persistencia, aqui es donde se definiria, no antes |

## Reglas esenciales (frontend)

- **Tipado explicito, sin `any`** — ya lo fuerza `tsconfig.json` (`strict: true`)
  y lo refuerza ESLint (`typescript-eslint` recomendado).
- **Un componente, una responsabilidad, un archivo** — `RequirementCard.tsx`
  es la referencia de alcance correcto para un componente nuevo.
- **Las vistas no deben acumular logica de negocio.** Hoy `App.tsx` ya tiene
  algo de logica de transformacion (`updateRequirement` recalculando
  `missing_requirements`) — aceptable mientras sea pequeño, pero si PB-02
  agrega calculo o transformacion de datos visible en el frontend, esa
  logica va en un servicio (`src/api/`, que ya existe para llamadas HTTP y
  se puede ampliar), no directo en el componente.
- **Toda llamada a la API pasa por `src/api/`** — nunca un `fetch` suelto
  dentro de un componente. Ya es el patron (`businessCases.ts`).
- **Tipos de datos compartidos en un solo lugar** (`src/types.ts`) — no
  duplicar la forma de un dato en cada componente que lo usa.

## GitHub Workflow

Ahora mismo el repo solo tiene `main` y una rama personal (`santiago`) — no
existe `dev`. Antes de adoptar el modelo de 3 niveles del documento de
referencia, decidan: ¿vale la pena la rama `dev` intermedia para un equipo
de 2 personas en un sprint de 1-2 semanas, o prefieren simplificar a
`feature/* → PR directo a main con revision del otro`? Lo segundo es menos
proceso y probablemente suficiente para este tamano de equipo — pero es
decision de ustedes, no mia.

Lo que sí es directamente aplicable sin importar cuál elijan (es agnóstico
al framework):

### Nombres de rama

```
feature/<descripcion-corta-en-minusculas-con-guiones>
```
Ejemplos: `feature/pb02-tabla-compatibilidad`, `feature/pb02-scoring`.

### Commits atomicos

Un commit, un cambio. Nada de mezclar un fix con una funcionalidad nueva.

### Prefijos de commit

- `feat:` funcionalidad nueva
- `fix:` correccion de error
- `update:` mejora o modificacion de algo existente
- `refactor:` reestructuracion sin cambiar comportamiento
- `docs:` documentacion
- `style:` formato, sin cambios de logica
- `test:` pruebas
- `chore:` mantenimiento (dependencias, config, tooling)

Modo imperativo: `feat: add scoring engine`, no `added scoring engine`.

### Antes de abrir un PR

```powershell
ruff check backend && ruff format backend --check
npm run lint --prefix frontend
```

## Commits y revision del motor de decision

Un commit que toca el motor de decision (tabla de compatibilidad, calculo
de pesos, scoring) necesita que quien lo escribe pueda explicar en una
frase *por que* esa logica es correcta — no solo que "los tests pasan".
Coherente con el objetivo de poder defender el proyecto, no solo de que
funcione.
