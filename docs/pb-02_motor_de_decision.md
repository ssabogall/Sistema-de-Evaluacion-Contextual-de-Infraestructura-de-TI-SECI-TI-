# PB-02: Motor de decisión (SAW) — cambios y archivos

Registro de lo que se creó o modificó para el motor de decisión, su ranking de prioridades,
su endpoint, el guardado de casos y las pantallas, con el propósito de cada archivo. Estado
al 13 de octubre de 2026.

## Alcance

El motor recibe los seis requisitos ya confirmados (PB-01) y, opcionalmente, el
ranking de prioridades del usuario. Devuelve la arquitectura recomendada (A, B o C),
los puntajes de las tres, si hubo trade-off y un mensaje explicativo. Es
**determinístico**: no usa IA en ninguna etapa. La IA solo interviene antes, en PB-01,
para transcribir lenguaje natural a variables.

Además del motor, este documento cubre lo que lo conecta con el usuario: la captura del
ranking de prioridades (contrato, prompt y bloque editable), el endpoint que evalúa y
guarda cada caso, el almacenamiento en SQLite y las pantallas con URL propia
(`/casos/<id>`).

Fuera de este alcance: plantillas CloudFormation, despliegue y validación con k6/CloudWatch.

## Flujo

```
Texto del caso ─► extractor (Gemini/OpenAI) ─► 6 requisitos + ranking SOLO si el texto lo dice
                                           │
                  usuario revisa y edita ◄─┘ (pantalla de revisión)
                                           │ POST /api/cases
                                           ▼
evaluate(requirements, ranking)   # app/decision_engine/engine.py
   levels = {key: r.value.value for key, r in reqs.canonical_items()}
   weights = rank_to_weights(ranking.to_engine_ranking())   # None -> pesos iguales
   contributions = score_by_variable(levels, weights)
   result = select(contributions)
   message = build_message(result, contributions, unknown_variables(levels))
                                           │
                                           ▼
CaseService.create ─► CaseRepository.save (SQLite) ─► id ─► /casos/<id>
```

## Resumen de archivos

Todas las rutas son relativas a `backend/`.

| Archivo | Tipo | Para qué sirve |
|---|---|---|
| `app/decision_engine/architectures.py` | existente | Enum `ArchitectureId` (A, B, C). Sin cambios. |
| `app/decision_engine/compatibility_table.py` | modificado | Tabla de compatibilidad (−2 a +3) y `get_score`. |
| `app/decision_engine/weights.py` | **nuevo** | Convierte el ranking del usuario en un peso por variable. |
| `app/decision_engine/scoring.py` | **nuevo** | Calcula peso × puntaje por arquitectura y variable. |
| `app/decision_engine/selection.py` | **nuevo** | Elige ganador, calcula margen y detecta trade-off. |
| `app/decision_engine/explanation.py` | **nuevo** | Arma el mensaje final con plantilla fija. |
| `app/decision_engine/engine.py` | **nuevo** | `evaluate()` orquesta los pasos y devuelve `Recommendation` (resultado completo y auditable). |
| `app/schemas/business_case.py` | modificado | Enum `BusinessPriorityStatement`, modelo `PriorityRanking` y campos `priority_ranking*` en análisis, confirmación y caso confirmado. |
| `app/ai/prompts/business_case_extractor.py` | modificado | Reglas 2 y 10 ajustadas, sección de prioridades (solo transcripción) y corrección de `near_zero` → `low`. |
| `app/ai/gemini_extractor.py` | modificado | El esquema que se le pide a Gemini incluye los dos campos del ranking. |
| `app/persistence/models.py` | **nuevo** | `CaseRecord` (caso guardado) y `CaseSummary` (fila del listado). |
| `app/persistence/repository.py` | **nuevo** | Interfaz `CaseRepository` y `CaseStorageError`. Lo único que conoce el resto del sistema. |
| `app/persistence/sqlite_repository.py` | **nuevo** | Implementación en SQLite con la librería estándar. |
| `app/services/case_service.py` | **nuevo** | Evalúa un caso confirmado, le asigna id y fecha y lo guarda. |
| `app/services/business_case_service.py` | modificado | `confirm` conserva el ranking. |
| `app/api/cases.py` | **nuevo** | `POST /api/cases`, `GET /api/cases`, `GET /api/cases/{id}`. |
| `app/config.py`, `app/main.py` | modificado | `database_path` y la inyección del repositorio en `create_app`. |
| `.gitignore`, `.env.example` | modificado | Se ignora `data/` y `*.sqlite3`; se documenta `DATABASE_PATH` (opcional). |
| `tests/test_compatibility_table.py` | **nuevo** | Verifica la tabla y `get_score`. |
| `tests/engine_fixtures.py` | **nuevo** | Datos compartidos por los tests (caso de la sección 5 del documento del motor). |
| `tests/test_weights.py` | **nuevo** | Verifica la conversión ranking → pesos. |
| `tests/test_scoring.py` | **nuevo** | Verifica contribuciones y manejo de `unknown`. |
| `tests/test_selection.py` | **nuevo** | Verifica ganador, trade-off y desempates. |
| `tests/test_explanation.py` | **nuevo** | Verifica el texto del mensaje. |
| `tests/test_engine_invariants.py` | **nuevo** | Propiedad que debe cumplirse en todas las combinaciones posibles. |
| `tests/test_priority_ranking.py` | **nuevo** | Modelo del ranking, contrato, API, esquemas para los proveedores y prompt. |
| `tests/test_engine.py` | **nuevo** | `evaluate()`: pesos según el ranking, caída a pesos iguales, `unknown` e ida y vuelta a JSON. |
| `tests/test_sqlite_repository.py` | **nuevo** | Guardar/leer, persistencia entre instancias, orden, errores del almacenamiento. |
| `tests/test_cases_api.py` | **nuevo** | Crear, consultar, listar, 404, 422 y 503 de los endpoints de casos. |
| `tests/conftest.py` | modificado | El cliente de pruebas usa un SQLite temporal, nunca la base real. |
| `frontend/src/…` | ver sección *Frontend* | Rutas, bloque de prioridades, página del caso y listado. |
| `docs/pb-02_motor_de_decision.md` | **nuevo** | Este documento. |

## Detalle por archivo

### `compatibility_table.py` (modificado)

- `COMPATIBILITY_TABLE`: variable → nivel → arquitectura → puntaje. Transcrita de la
  sección 3 de `motor_de_reglas_puntaje_ponderado.md`; si se cambia un valor, hay que
  cambiarlo también allá.
- Correcciones respecto a la primera versión **del archivo** (la transcripción inicial al
  código). Los valores del documento no cambiaron: el código tenía tres errores de
  transcripción frente a la sección 3. `DEMAND_PATTERN` usaba `StandardLevel` en lugar de
  `DemandPattern` (nunca habría coincidido); su fila de picos impredecibles tenía
  `(−2, 0, −1)` y debía ser `(−2, +1, +2)`; y `EXPECTED_LOAD_VOLUME` nivel alto, arquitectura
  C, tenía `−1` y debía ser `+2`.
- `CompatibilityLookupError`: excepción tipada para combinaciones que no existen en la
  tabla (nivel equivocado para la variable, o `unknown`).
- `get_score(key, level, architecture) -> float`: busca el puntaje. `level` se recibe como
  `str`; funciona con cualquiera de los `StrEnum` del esquema porque se comparan por valor.
- Se eliminaron `_row` y `ARCHITECTURES_IN_ORDER`, que no se usaban.

### `weights.py`

- `RANK_WEIGHTS = (0.325, 0.275, 0.225, 0.175)`: peso del pilar según su posición en el
  ranking (fórmula suavizada).
- `STATEMENT_VARIABLES`: cada afirmación de negocio gobierna las variables de su pilar.

  | Afirmación (`BusinessPriorityStatement`) | Pilar | Variables |
  |---|---|---|
  | `NEVER_STOP_WORKING` | Reliability | tolerancia a interrupción, criticidad de continuidad |
  | `LOWEST_COST` | Cost Optimization | presupuesto disponible |
  | `FAST_UNDER_LOAD` | Performance Efficiency | patrón de demanda, volumen de carga |
  | `PROTECT_INFORMATION` | Security | sensibilidad de la información |

- `is_complete_ranking(ranking)`: verdadero solo si están las 4 afirmaciones con las
  posiciones 1, 2, 3 y 4 sin repetir.
- `rank_to_weights(ranking)`: devuelve un peso por cada una de las 6 variables (suman 1),
  repartiendo el peso del pilar en partes iguales entre sus variables. Si el ranking es
  `None`, está incompleto o es inválido, usa 25 % por pilar.

### `scoring.py`

- `UNKNOWN_SCORE = 0.5`: valor neutro (punto medio de la escala) para variables sin dato.
  Se suma igual a las tres arquitecturas, así que no cambia cuál gana.
- `unknown_variables(requirements)`: variables cuyo nivel es `unknown` (incluye las que
  PB-01 marcó como `conflict`, que el esquema normaliza a `unknown`).
- `score_by_variable(requirements, weights)`: devuelve
  `{arquitectura: {variable: peso × puntaje}}`. Recibe solo el diccionario de niveles, no
  el `ConfirmedBusinessCase`, para no depender del contrato HTTP. Lanza `ValueError` si
  falta alguna variable o peso, y deja pasar `CompatibilityLookupError` si un nivel no
  corresponde a su variable.

### `selection.py`

- `TRADE_OFF_RATIO = 0.20`: hay trade-off si el margen entre el 1.º y el 2.º es menor al
  20 % del total del ganador (comparación estricta).
- `ROUND_DIGITS = 9`: los totales se redondean para que los empates sean exactos y el
  borde del umbral no dependa del ruido de coma flotante.
- `SelectionResult` (Pydantic, inmutable, `extra="forbid"`): `winner`, `runner_up`,
  `totals`, `margin`, `trade_off`, `tie_broken`, `deltas` (ganador − segundo por
  variable; negativo favorece al segundo) y `separating_variables` (variables con delta
  distinto de cero, de mayor a menor valor absoluto).
- `select(contributions)`: suma, ordena y calcula lo anterior. En un empate exacto gana la
  primera arquitectura en el orden del catálogo (A, luego B, luego C) y `trade_off` es
  siempre verdadero.

### `explanation.py`

- `build_message(result, contributions, unknown_variables=())`: texto con plantilla fija,
  sin IA. Se compone de: (1) la arquitectura recomendada y su puntaje; (2) hasta dos
  variables de mayor contribución ponderada del ganador, excluyendo las `unknown` y las
  de contribución no positiva; (3) si hubo trade-off, que la segunda quedó cerca (o que
  hubo empate) y en qué variables estaba mejor; (4) una nota con las variables sin
  información y el valor neutro aplicado.
- `ARCHITECTURE_LABELS` y `VARIABLE_LABELS`: textos en lenguaje de negocio.
- `unknown_variables` es un parámetro opcional que no estaba en el plan original. Sin él,
  un dato faltante (0.5) podía aparecer como razón a favor del ganador.

### `business_case.py` (modificado)

- `BusinessPriorityStatement`: las 4 afirmaciones del ranking. El texto completo de cada
  una está en la sección 4 del documento del motor.
- `PriorityRanking`: cuatro campos fijos (`never_stop_working`, `lowest_cost`,
  `fast_under_load`, `protect_information`) con la posición 1 a 4 o `null`. Rechaza posiciones
  repetidas o fuera de rango. Un orden vacío o incompleto es válido. `to_engine_ranking()`
  devuelve el diccionario que espera `rank_to_weights`, o `None` si no está completo.
  Se usa un objeto fijo en lugar de un diccionario abierto porque los modos estrictos de los
  proveedores de IA rechazan los diccionarios abiertos; tampoco usa `ge`/`le` en el esquema
  JSON por la misma razón (el rango se valida en un validador).
- `BusinessCaseAnalysis`: `priority_ranking` y `priority_ranking_evidence` (con valor por
  defecto, así que los payloads anteriores siguen siendo válidos; sin ranking, la evidencia
  se descarta). `BusinessCaseConfirmationRequest` y `ConfirmedBusinessCase` llevan
  `priority_ranking`.

### Prompt del extractor (modificado)

- Regla 2: se permiten las seis variables y el ranking; regla 10: ya no prohíbe "ranking"
  sino "pesos", y limita el orden al que el caso expresa explícitamente.
- Sección nueva: el modelo transcribe el orden **solo** si el texto lo dice, copia la
  evidencia literal, **nunca lo infiere** y deja `null` lo que no se ordenó.
- Corrección: el prompt hablaba de `near_zero`, que no existe en el esquema; ahora dice `low`.

### `engine.py`

- `evaluate(requirements, ranking) -> Recommendation`: único lugar que conoce el orden de los
  pasos. Cada paso sigue en su módulo.
- `Recommendation`: arquitectura ganadora y segunda, totales, margen, `trade_off`,
  `tie_broken`, mensaje, pesos usados, `weights_source` (`ranking` o `equal`), variables
  desconocidas y la contribución de cada variable a cada arquitectura. Guarda todo lo
  necesario para auditar la decisión sin recalcular.

### Persistencia (`app/persistence/`)

- `CaseRepository` (interfaz): `save`, `get`, `list_recent`. Ningún otro módulo conoce SQLite.
  **Si el almacenamiento pasa a un servicio de AWS** (DynamoDB, RDS…), solo hay que escribir
  otra implementación de esta interfaz y cambiarla en `create_app`.
- `SqliteCaseRepository`: una tabla `cases` (id, fecha, arquitectura, trade-off, texto del
  caso y dos columnas JSON con el caso confirmado y la recomendación). Una conexión por
  operación (seguro con los hilos de FastAPI); el archivo y la tabla se crean la primera
  vez que se usa, no al importar la aplicación. Cualquier fallo de SQLite o un registro que
  ya no coincide con el esquema se convierte en `CaseStorageError`.
- Ruta del archivo: `DATABASE_PATH` en `.env` (opcional); por defecto `data/seci_ti.sqlite3`
  en la raíz del repositorio, que está en `.gitignore`. Para empezar de cero basta borrar el
  archivo.

### API de casos (`app/api/cases.py`)

| Método y ruta | Qué hace | Respuestas |
|---|---|---|
| `POST /api/cases` | Recibe el mismo cuerpo que `/confirm`, calcula la recomendación y guarda el caso | 201 con el caso completo; 422 si el cuerpo es inválido (p. ej. posiciones repetidas); 503 si falla el almacenamiento |
| `GET /api/cases` | Casos recientes (más nuevo primero, `limit` 1 a 200) | 200; 503 |
| `GET /api/cases/{id}` | Un caso completo | 200; 404 `"No encontramos ese caso."`; 503 |

`POST /api/business-cases/confirm` se mantiene sin cambios (contrato de PB-01). Los mensajes
de error 503 son genéricos; el detalle solo queda en el log del servidor.

### Frontend (`frontend/src/`)

- **Rutas sin dependencia nueva** (`router.ts`, `components/Link.tsx`): `/` análisis y
  revisión, `/casos` listado, `/casos/<id>` resultado de un caso. Usa la History API; si el
  proyecto crece se puede cambiar por `react-router` sin tocar las páginas.
- `pages/AnalyzePage.tsx`: el flujo de PB-01 que estaba en `App.tsx`. "Confirmar y ver
  recomendación" crea el caso y navega a `/casos/<id>`.
- `pages/CasePage.tsx`: recomendación, puntaje de las tres arquitecturas (escala −2 a +3),
  pesos usados y de dónde salen, tabla de cálculo por variable, caso original y botón para
  copiar el enlace.
- `pages/CasesListPage.tsx`: registro de casos guardados.
- `components/PriorityRankingPanel.tsx` + `priorityRanking.ts`: bloque editable de
  prioridades con estados *Sin definir / Incompleto / Detectado en tu texto / Editado por ti*;
  si se elige una posición ocupada, las dos se intercambian.
- Tipos y cliente: `types.ts`, `api/cases.ts`, `architectures.ts`, `format.ts`.
- Tests: `App.test.tsx` (14), `priorityRanking.test.ts` (7) y `router.test.ts` (3).

## Decisiones de diseño

| Tema | Decisión | Razón |
|---|---|---|
| Pesos del ranking | 32.5 / 27.5 / 22.5 / 17.5 % | El pilar menos prioritario conserva un peso relevante. |
| Variable `unknown` | 0.5 | Punto medio real de −2..+3; no altera el ganador. |
| Ranking ausente o inválido | 25 % por pilar | Sin ciclo de reenvío; la responsabilidad es del usuario. |
| Umbral de trade-off | 20 % del total del ganador, estricto | Tasa de aviso estable (34 % a 41 %) con hasta 5 variables `unknown`; con las 6 desconocidas las tres arquitecturas empatan siempre. |
| Alternativa descartada | Umbral absoluto (p. ej. 0.25) | Avisaba en 36 % de los casos sin datos faltantes y hasta 64 % con 5 variables `unknown`. |
| Desempate exacto | Orden del catálogo A → B → C | Determinístico y fácil de explicar. |
| Mensaje final | Plantilla fija | Trazabilidad: todo sale de números ya calculados. |
| Contrato de salida | Modelo Pydantic inmutable | Convención de `convenciones.md`. |
| Captura del ranking | El LLM solo transcribe un orden explícito; el usuario lo edita y confirma | El LLM no decide los pesos; el motor sigue siendo determinístico. Inferirlo contaría dos veces la misma evidencia y sesgaría al usuario. |
| Almacenamiento | SQLite detrás de la interfaz `CaseRepository` | Sin infraestructura nueva para el capstone; cambiar a un servicio de AWS no toca el resto del código. |
| Qué se guarda | El caso confirmado y la recomendación completa, con pesos y contribuciones | Trazabilidad contexto → decisión (y más adelante → evidencia de k6/CloudWatch) sin recalcular. |
| Rutas del frontend | Router mínimo propio con la History API | Tres rutas no justifican una dependencia nueva. |
| Ranking inválido del modelo | Se trata como error del proveedor (503 genérico) | Es la ruta más simple; se puede volver más tolerante (descartar el ranking y avisar). |

## Validación

- `pytest tests -v` en la máquina del equipo (12-oct-2026): 100 pasaron, 6 se omitieron
  (integración con el proveedor de IA).
- 13-oct-2026, en un entorno sin FastAPI (no se pudo instalar): 126 pruebas del backend
  pasaron y 18 (las que usan el cliente HTTP) se omitieron; `ruff check` sin errores en lo
  nuevo. Los tests de API de `test_cases_api.py`, `test_priority_ranking.py` y
  `test_business_case_api.py` **hay que correrlos en la máquina del equipo**.
- Frontend (13-oct-2026): `tsc --noEmit`, ESLint y Prettier sin errores. Los tests de
  Vitest **no se pudieron ejecutar** (los `node_modules` son de Windows) y hay que correrlos
  con `npm test`.
- Prueba manual del ranking con Gemini (13-oct-2026): los cuatro casos de prueba se
  comportaron como se esperaba (orden completo, parcial, sin orden y sin orden inferido).
- Contraste independiente: el motor se comparó contra una simulación con fracciones
  exactas en 98 304 escenarios (4 096 combinaciones de niveles × 24 rankings): 0
  discrepancias en totales, trade-off y empates.
- Se reintrodujeron 8 errores a propósito (umbral, `<` por `<=`, redondeo, desempate,
  valor de `unknown`, pesos, filtro de `unknown` en el mensaje) y los tests detectaron
  los 8.
- Datos de la simulación: el total del ganador nunca fue menor a 0.45; hubo trade-off en
  34 % (datos completos) a 35 % (con `unknown`) de los casos; hubo empate exacto en
  0.85 % y 1.57 % respectivamente.

### Qué verifica cada test

| Archivo | Pruebas | Qué comprueba |
|---|---|---|
| `test_compatibility_table.py` | 21 | La tabla cubre todas las variables, con los niveles correctos, las 3 arquitecturas y valores en rango; `get_score` y su error. |
| `test_weights.py` | 32 | Los pesos suman 1 para los 24 rankings posibles; valores suavizados; caída a pesos iguales con ranking nulo, incompleto, repetido o fuera de rango. |
| `test_scoring.py` | 10 | Reproduce el ejemplo numérico del documento (A −0.35, B 1.70, C 1.40); `unknown` vale 0.5 × peso; errores por datos faltantes o nivel ajeno. |
| `test_selection.py` | 9 | Ganador y trade-off del ejemplo; borde exacto del umbral; empates; ruido de coma flotante. |
| `test_explanation.py` | 5 | Mensaje exacto del ejemplo; las `unknown` nunca se presentan como razón; empate; caso sin contribuciones positivas. |
| `test_priority_ranking.py` | 25 | Campos = afirmaciones; posiciones repetidas o fuera de rango; ranking → pesos del motor; contrato; API; esquemas sin diccionarios abiertos ni `minimum`/`maximum`; prompt sin `near_zero`. |
| `test_engine.py` | 6 | `evaluate()`: trazabilidad de la recomendación, pesos por ranking o iguales, `unknown`, ida y vuelta a JSON. |
| `test_sqlite_repository.py` | 10 | Guardar y leer, persistencia entre instancias, nada en disco hasta el primer uso, id duplicado, orden y límite del listado, extracto, registro ilegible, ruta inválida. |
| `test_cases_api.py` | 8 | Crear (201), consultar, sobrevivir a una instancia nueva, 404, listado, 422 por posiciones repetidas, 503 sin filtrar detalles internos. |
| `test_engine_invariants.py` | 1 | El total del ganador es positivo en todas las combinaciones. Es lo que justifica el umbral relativo: si alguien cambia la tabla y falla, hay que revisar `TRADE_OFF_RATIO`. |

## Pendientes y supuestos por confirmar

- **Correr las pruebas en la máquina del equipo** (backend y frontend): ver abajo.
- **Supuestos por confirmar:** el umbral relativo del 20 % y el desempate por orden del
  catálogo se asumieron; ambos son constantes de una línea en `selection.py`.
- **Validar la tabla de compatibilidad** con Miguel y, si es posible, con el profesor.
- **Ranking inválido del modelo:** hoy produce el error genérico; se puede degradar a
  "sin ranking" con una advertencia.
- **Almacenamiento:** SQLite vive en el disco donde corra el backend. Para la trazabilidad
  desde AWS habrá que implementar otro `CaseRepository` (DynamoDB o RDS) y decidir si hay que
  migrar los casos ya guardados.
- **Gemini:** la implementación sigue sin aplicar el timeout configurado ni distinguir una
  clave inválida (decisiones que se dejaron al equipo).
- **Limpieza con `ruff`:** `ruff format --check` marca archivos que ya venían así
  (`compatibility_table.py`, una línea en blanco en `business_case.py`).
- **Hacer commit** de estos cambios siguiendo `convenciones.md`.
- **Fuera de este documento:** plantillas CloudFormation, despliegue y validación con k6 y
  CloudWatch.

## Cómo ejecutar los tests

Desde `backend/`, en PowerShell:

```
pytest tests -v
ruff check .
ruff format . --check
```

(En PowerShell 5 el operador `&&` no existe; ejecutar cada comando por separado.)

Frontend, desde `frontend/`:

```
npm test
npm run lint
npm run build
```

## Cómo probarlo a mano

1. Terminal 1, desde la raíz del repositorio: `.\.venv\Scripts\Activate.ps1` y luego
   `uvicorn app.main:app --app-dir backend --reload`.
2. Terminal 2: `cd frontend` y `npm run dev`; abrir `http://localhost:5173`.
3. Analizar un caso, revisar el bloque de prioridades, confirmar y comprobar que la URL pasa
   a `/casos/<id>`.
4. Recargar la página: el caso debe seguir ahí. Abrir `/casos`: debe aparecer en el listado.
5. Reiniciar el backend y volver a abrir la URL: el caso sigue guardado (está en
   `data/seci_ti.sqlite3`).
