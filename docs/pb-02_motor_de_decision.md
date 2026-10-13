# PB-02: Motor de decisión (SAW) — cambios y archivos

Registro de lo que se creó o modificó para el núcleo del motor de decisión, con el
propósito de cada archivo. Estado al 12 de octubre de 2026.

## Alcance

El motor recibe los seis requisitos ya confirmados (PB-01) y, opcionalmente, el
ranking de prioridades del usuario. Devuelve la arquitectura recomendada (A, B o C),
los puntajes de las tres, si hubo trade-off y un mensaje explicativo. Es
**determinístico**: no usa IA en ninguna etapa. La IA solo interviene antes, en PB-01,
para transcribir lenguaje natural a variables.

Fuera de este alcance: captura del ranking en el contrato/prompt/frontend (paso 2),
endpoint y UI (paso 7), plantillas CloudFormation y validación con k6/CloudWatch.

## Flujo

```
Requirements (PB-01) ─► levels = {key: r.value for key, r in reqs.canonical_items()}
ranking del usuario  ─► weights = rank_to_weights(ranking)           # None -> pesos iguales
                        contributions = score_by_variable(levels, weights)
                        result = select(contributions)
                        message = build_message(result, contributions, unknown_variables(levels))
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
| `app/schemas/business_case.py` | modificado | Se agregó el enum `BusinessPriorityStatement` y el alias `BusinessPriorityRanking`. |
| `tests/test_compatibility_table.py` | **nuevo** | Verifica la tabla y `get_score`. |
| `tests/engine_fixtures.py` | **nuevo** | Datos compartidos por los tests (caso de la sección 5 del documento del motor). |
| `tests/test_weights.py` | **nuevo** | Verifica la conversión ranking → pesos. |
| `tests/test_scoring.py` | **nuevo** | Verifica contribuciones y manejo de `unknown`. |
| `tests/test_selection.py` | **nuevo** | Verifica ganador, trade-off y desempates. |
| `tests/test_explanation.py` | **nuevo** | Verifica el texto del mensaje. |
| `tests/test_engine_invariants.py` | **nuevo** | Propiedad que debe cumplirse en todas las combinaciones posibles. |
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

Solo se agregaron 18 líneas, antes de `ServiceInterruptionTolerance`:

- `BusinessPriorityStatement`: las 4 afirmaciones del ranking. El texto completo de cada
  una sigue en la sección 4 del documento del motor.
- `BusinessPriorityRanking = dict[BusinessPriorityStatement, int]`: posición elegida por
  el usuario (1 = la más importante).

El campo todavía **no** está en `BusinessCaseAnalysis` ni en `BusinessCaseConfirmationRequest`.

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

## Validación

- `pytest tests -v` en la máquina del equipo (12-oct-2026): 100 pasaron, 6 se omitieron
  (integración con el proveedor de IA).
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
| `test_engine_invariants.py` | 1 | El total del ganador es positivo en todas las combinaciones. Es lo que justifica el umbral relativo: si alguien cambia la tabla y falla, hay que revisar `TRADE_OFF_RATIO`. |

## Pendientes y supuestos por confirmar

- **Supuestos por confirmar:** el umbral relativo del 20 % y el desempate por orden del
  catálogo se asumieron; ambos son constantes de una línea en `selection.py`.
- **Paso 2:** agregar el ranking al contrato (`BusinessCaseAnalysis`,
  `BusinessCaseConfirmationRequest`), al prompt de los extractores de OpenAI y Gemini y al
  frontend. El LLM solo transcribe lo que el usuario dice; nunca infiere el ranking.
- **Paso 7:** endpoint y UI mínima.
- **Actualizar `motor_de_reglas_puntaje_ponderado.md`:** las secciones 4.1, 6 y 8 siguen
  marcando como pendiente lo ya decidido. El ejemplo de la sección 5 usa pesos lineales;
  con los pesos suavizados el mismo caso da margen 0.3375 contra un umbral de 0.3325, así
  que ya no dispara trade-off. Además, su texto dice que C era mejor en tolerancia a
  interrupción, pero según la tabla (nivel medio: B +2, C +1) solo es mejor en criticidad.
- **Validar la tabla de compatibilidad** con Miguel y, si es posible, con el profesor.
- **Limpieza con `ruff`** en `compatibility_table.py` (orden de imports y formato).
- **Hacer commit** de estos cambios siguiendo `convenciones.md`.

## Cómo ejecutar los tests

Desde `backend/`, en PowerShell:

```
pytest tests -v
ruff check .
ruff format . --check
```

(En PowerShell 5 el operador `&&` no existe; ejecutar cada comando por separado.)
