# SECI-TI: guía de presentación de avances

Resumen condensado de cada tema a presentar, en el orden sugerido. Cada sección tiene la
idea central, los datos para sostenerla y el archivo donde está el detalle.

**Estado a 19 de octubre de 2026.** Núcleo de decisión terminado (extracción → motor →
registro → pantallas). Falta la parte de infraestructura real: CloudFormation, despliegue
en AWS y validación con k6 y CloudWatch. Quedan unas 4 semanas del cronograma.

---

## 0. Resumen en 30 segundos

SECI-TI recibe la descripción de un caso de negocio en lenguaje natural, la convierte en seis
variables validadas, y un **motor determinístico** recomienda una de tres arquitecturas AWS
(A básica, B escalable, C resiliente), explicando por qué. La IA solo transcribe lenguaje;
**nunca decide**. Cada decisión queda guardada y es consultable por URL. La siguiente fase
despliega la arquitectura elegida con CloudFormation y comprueba con k6 y CloudWatch si
cumple lo que el caso pedía.

---

## 1. Problema y pregunta del proyecto

- Las necesidades del negocio ("no podemos caernos en Black Friday") no dicen qué
  infraestructura usar. Entre una y otra hay una brecha que hoy se cubre con intuición.
- Una mala decisión da infraestructura insuficiente o gasto innecesario.
- **Pregunta guía:** ¿cómo traducir requisitos de negocio en decisiones de infraestructura
  justificables y validar experimentalmente que cumplen?
- El foco es **Infraestructura de TI**; la aplicación web es solo la interfaz que integra el flujo.
- Alcance: infraestructura **nueva** (no analizamos ni migramos infraestructura existente).

Detalle: `contexto_proyecto_capstone.md` (Proyecto), `docs/requisitos.md`.

## 2. Flujo completo y qué parte está hecha

```
Caso de negocio → IA extrae 6 variables → usuario revisa y confirma
   → motor SAW → arquitectura recomendada + explicación → se guarda (URL por caso)
   → [pendiente] CloudFormation → despliegue (Boto3) → k6 + CloudWatch → validación
```

| Etapa | Estado |
|---|---|
| Extracción de requisitos con IA (PB-01) | Hecho |
| Revisión y confirmación humana | Hecho |
| Motor de decisión SAW (PB-02) | Hecho |
| Captura editable de prioridades (ranking) | Hecho |
| Registro de casos (SQLite) y URL por caso | Hecho |
| Plantillas CloudFormation A/B/C | Pendiente (carpetas creadas) |
| Despliegue automatizado con Boto3 | Pendiente |
| Pruebas de carga k6 y métricas CloudWatch | Pendiente |

## 3. Decisión de diseño central: la IA no decide

- El LLM **solo extrae** (texto → JSON con esquema cerrado). La recomendación sale de un
  motor de reglas determinístico: mismas entradas, misma salida, y se puede auditar.
- Se descartó que el LLM elija arquitectura o ejecute acciones: lo vuelve decisor, no es
  reproducible y abre riesgos operativos. MCP y Boto3 son cosas distintas; Boto3 solo
  ejecuta *después* de la decisión.
- Se hizo cumplir en el código: los modelos Pydantic usan `extra="forbid"`, así que una
  arquitectura no puede colarse en la respuesta de la IA. El texto original lo restaura el
  backend aunque el proveedor lo modifique.
- **Frase para defenderlo:** "la IA entiende el lenguaje; el criterio de ingeniería está en
  reglas que el equipo definió y puede explicar".

## 4. De dónde salen las seis variables

- Síntesis de los **Well-Architected Frameworks** de AWS, Azure y GCP, quedándonos con los
  cuatro pilares que coinciden: Reliability, Security, Cost Optimization, Performance
  Efficiency.
- Se excluyeron Operational Excellence y Sustainability (sección 7 de la síntesis): las tres
  arquitecturas comparten IaC y CloudWatch y viven en el mismo entorno, así que ninguno
  de los dos pilares permite diferenciarlas.
- Descartado también: CNCF (su alcance de Kubernetes/contenedores no encaja con EC2 + ALB + ASG).

| Variable | Pilar | Niveles |
|---|---|---|
| Tolerancia a interrupción | Reliability | alta / media / baja |
| Criticidad para el negocio | Reliability | baja / media / alta |
| Sensibilidad de la información | Security | baja / media / alta |
| Presupuesto disponible | Cost | bajo / medio / alto |
| Patrón de demanda | Performance | constante / picos predecibles / impredecibles |
| Volumen de carga | Performance | bajo / medio / alto |

- "Prioridad de costo" se eliminó como variable aparte para no duplicar: el costo como
  *hecho* es el presupuesto; el costo como *preferencia* lo captura el ranking.

Detalle: `docs/sintesis_pilares_waf_seci-ti.md`.

## 5. Extracción de requisitos con IA (PB-01)

- FastAPI + Pydantic en el backend; React + TypeScript en el frontend.
- Cada variable devuelve **valor, estado y evidencia**: `detected` (con cita literal del
  texto), `unknown` (sin evidencia) o `conflict` (afirmaciones contradictorias, no se
  resuelve solo).
- **Sin umbrales inventados:** "120 solicitudes por segundo" sin calificativo no se clasifica
  como carga alta; se conserva el número como contexto y la variable queda "No definida"
  para que la complete el usuario.
- **Proveedor de IA intercambiable:** interfaz `AIRequirementExtractor` con dos
  implementaciones, OpenAI y Gemini (capa gratuita), elegidas con `AI_PROVIDER`. El resto
  del sistema no sabe cuál se usa.
- **Caso real de robustez:** Gemini devolvió `unknown` marcado como `detected` (una
  contradicción). El esquema la rechazó con razón; se agregó una normalización acotada en
  el extractor y se aclaró el prompt. Otras respuestas inválidas siguen fallando.
- Confirmación humana obligatoria: el resultado de la IA nunca es final sin revisión.

Detalle: `docs/pb-01_extraccion_requisitos.md`.

## 6. Motor de decisión SAW (PB-02)

**Modelo:** Simple Additive Weighting, técnica estándar de decisión multicriterio.

> Puntaje(arquitectura) = Σ peso(variable) × compatibilidad(arquitectura, nivel de la variable)

- **Tabla de compatibilidad** (escala −2 a +3): define qué tan bien encaja cada
  arquitectura con cada nivel de cada variable. Vive en Python, en un módulo propio. Ejemplo:
  con tolerancia a interrupción baja, A = −2, B = 0, C = +3.
- **Pesos:** vienen del orden de prioridades del usuario, suavizados: 32,5 / 27,5 / 22,5 /
  17,5 % según la posición. Se eligió esta fórmula sobre la lineal (40/30/20/10) para que el
  pilar menos importante nunca quede casi anulado. El peso de cada pilar se reparte en
  partes iguales entre sus variables.
- **Sin ranking o ranking incompleto:** cada pilar pesa 25 %.
- **Variable desconocida:** puntúa 0,5, el punto medio del rango −2..+3, para no premiar ni
  castigar a ninguna arquitectura.
- **Trade-off:** si la diferencia entre el 1.º y el 2.º es menor al 20 % del puntaje del
  ganador, se avisa que la decisión es cercana y en qué variable ganaría la segunda. Un
  empate exacto cuenta como trade-off y gana A → B → C.
- **Explicación:** mensaje de plantilla fija (no generado por IA) que nombra las variables
  que más aportaron.
- **Descartada:** una regla que daba siempre más peso a la disponibilidad sin importar lo
  que dijera el usuario; los pesos salen solo de su ranking.

**Ejemplo numérico para tener a mano** (tolerancia media, criticidad alta, sensibilidad
media, presupuesto medio, picos predecibles, carga media; orden: 1.º continuidad, 2.º
rendimiento, 3.º costo, 4.º seguridad): **A = −0,2375, B = 1,6625, C = 1,3250**. Gana B.
El margen con C es 0,3375 y el umbral es 0,3325, así que no hay trade-off.

Módulos en `backend/app/decision_engine/`: `weights`, `scoring`, `selection`,
`explanation`, `compatibility_table`, `engine`. Detalle: `docs/motor_de_reglas_puntaje_ponderado.md`
y `docs/pb-02_motor_de_decision.md`.

## 7. Captura del orden de prioridades

- El usuario ordena cuatro afirmaciones en lenguaje de negocio (nunca ve "Reliability"):
  que nunca deje de funcionar, costo mínimo, rápida bajo carga, proteger la información.
- **Primero se evaluó** que la IA propusiera el orden a partir del contexto y se descartó: la
  convertiría en decisora. **Decisión final: solo explícito y editable.**
  - La IA transcribe un orden solo si el texto lo dice literalmente, con la cita como evidencia.
  - El usuario puede reordenarlo, quitarlo y debe confirmarlo.
  - Si no hay orden o queda incompleto, no hay insistencia: pesos iguales.
- La interfaz muestra el estado: "Detectado en tu texto", "Editado por ti", "Incompleto" o
  "Sin definir".

## 8. Registro de casos y trazabilidad

- Cada caso confirmado se guarda con la recomendación completa (puntajes, pesos,
  contribuciones por variable) y recibe su propia URL: `/casos/<id>`. Hay un listado en
  `/casos`.
- Almacenamiento: **SQLite** local detrás de una interfaz (`CaseRepository`). Es el paso
  previo a un servicio de AWS (DynamoDB o RDS), desde donde se hará la trazabilidad y la
  visualización; migrar es escribir otra implementación y cambiar una línea.
- Cada decisión se puede auditar después: qué texto entró, qué se confirmó, qué pesos y qué
  puntajes salieron.

## 9. Demo sugerida (3 minutos)

1. Pegar el caso de ejemplo (abajo) y pulsar "Analizar requisitos".
2. Mostrar las seis variables con su evidencia citada y el bloque de prioridades
   "Detectado en tu texto".
3. Cambiar una variable a mano (por ejemplo, tolerancia) para mostrar que el usuario manda.
4. "Confirmar y ver recomendación": se abre `/casos/<id>`. Mostrar la arquitectura, el
   mensaje, las barras de puntaje A/B/C, la fuente de los pesos y la tabla de cálculo.
5. Recargar la página y abrir `/casos`: el caso persiste.
6. Variante: "Quitar orden" en otro caso y mostrar que los pesos pasan a ser iguales.

**Caso de ejemplo** (tienda en línea; llena las seis variables, el contexto adicional y el orden):

```
Somos una tienda en línea de electrodomésticos que vende en Colombia y Ecuador. Esperamos
unos 15.000 usuarios registrados, con alrededor de 600 conectados al mismo tiempo en horas
pico, y unas 120 solicitudes por segundo, un volumen de tráfico alto para nuestro tamaño.
Esperamos que la base de clientes se duplique en los próximos 12 meses. Cada año tenemos
campañas como Black Friday y Cyber Monday con aumentos muy grandes de tráfico, pero fuera
de esas fechas también aparecen picos imprevistos cuando un influenciador menciona un
producto. Si la tienda se cae, perdemos ventas de inmediato y los clientes se van con la
competencia, así que no podemos tolerar interrupciones de más de unos pocos minutos; nuestra
meta es una disponibilidad del 99,9 %. Las páginas deben responder en menos de 2 segundos.
Manejamos datos personales de los clientes y los pagos con tarjeta, por lo que la
información es muy sensible. Contamos con un presupuesto mediano, de unos 2.500 USD
mensuales para la infraestructura. En cuanto a prioridades, lo primero es que la tienda
nunca deje de funcionar; en segundo lugar, proteger al máximo la información de los
clientes; en tercer lugar, que responda rápido aun con mucho tráfico; y por último,
mantener el costo lo más bajo posible.
```

Nota: "unos pocos minutos" puede salir como tolerancia media en lugar de baja. Es esperable
y se corrige en la revisión. Ensaya el caso antes de la presentación y anota qué arquitectura
sale.

## 10. Calidad y pruebas

- **Backend:** 149 tests pasados y 6 omitidos (de integración contra el proveedor real) en la
  última corrida completa, más 4 tests nuevos del extractor de Gemini. `ruff` sin errores.
  Cubren esquemas, tabla de compatibilidad, pesos, puntajes, selección, explicación,
  invariantes del motor, repositorio SQLite y API.
- **Frontend:** 24 tests con Vitest; además `tsc` y ESLint limpios.
- Las pruebas normales usan extractores falsos: no consumen tokens ni dependen de la red.
- **Invariantes del motor:** el puntaje del ganador es siempre mayor que 0 y los pesos suman 100 %.

## 11. Fuera de alcance (con razón)

- Analizar o migrar infraestructura existente (RF-06 a RF-11 y relacionados): pasó a
  `docs/ideas_futuras.md`.
- Generar arquitecturas desde cero: el catálogo es cerrado (A, B, C) por viabilidad.
- Un ranking universal de arquitecturas: solo se afirma la mejor opción *entre las tres*
  para ese caso y se valida con evidencia.
- Otros proveedores cloud y despliegues empresariales.
- Restricción real: AWS Academy Learner Lab (IAM, tiempo de sesión y presupuesto limitados).

## 12. Lo que sigue

1. **Validar la tabla de compatibilidad** con Miguel y, si se puede, con el profesor: son
   juicios de ingeniería, no verdades absolutas. Confirmar también el umbral de 20 % y el
   desempate A → B → C.
2. **Plantillas CloudFormation** de las tres arquitecturas (`infrastructure/architecture-a|b|c/`).
3. **Despliegue automatizado** con Python y Boto3 (crear stack, consultar estado, eliminar
   al terminar).
4. **Pruebas de carga con k6**, con escenarios derivados de lo que pidió el caso.
5. **Métricas en CloudWatch** (CPU, latencia y errores del ALB, actividad de Auto Scaling).
6. **Validación:** ¿la infraestructura desplegada soporta lo que el caso esperaba?
7. Mover el registro de casos a un servicio de AWS.

## 13. Preguntas probables y cómo responderlas

- **¿Por qué no dejar que la IA recomiende directamente?** Porque no sería reproducible ni
  auditable. Aquí la IA entiende el lenguaje y el criterio vive en reglas explícitas que el
  equipo puede explicar y ajustar.
- **¿De dónde salen los números de la tabla de compatibilidad?** Son un juicio de ingeniería
  del equipo, apoyado en la síntesis de los frameworks Well-Architected. Por eso es un
  componente declarado como pendiente de validación y es fácil de ajustar.
- **¿Qué pasa si el usuario no da prioridades?** Los cuatro pilares pesan igual (25 %), y la
  pantalla del caso lo indica.
- **¿Qué pasa si la IA se equivoca al interpretar?** Siempre hay revisión humana, con la
  evidencia citada. Las variables sin evidencia quedan "No definidas" en vez de adivinarse.
- **¿La seguridad no discrimina entre arquitecturas?** Poco, y es esperable: en Learner Lab
  las tres comparten el mismo modelo de seguridad de AWS.
- **¿Cómo saben que la recomendación es buena?** Esa es la fase de validación experimental
  (despliegue + k6 + CloudWatch). Hoy hay evidencia de que el motor es coherente y
  reproducible, pero todavía no del comportamiento real de las arquitecturas. Dilo con esa
  claridad.
- **¿Por qué SQLite?** Para tener registro y URL por caso sin depender de AWS todavía; está
  detrás de una interfaz para migrar sin tocar el resto.
- **¿Y si cambia el proveedor de IA?** Solo cambia una variable de entorno; el resto del
  sistema usa la interfaz.

## Dónde está cada cosa

| Tema | Archivo |
|---|---|
| Contexto y alcance | `contexto_proyecto_capstone.md` (Proyecto), `docs/requisitos.md` |
| Pilares y variables | `docs/sintesis_pilares_waf_seci-ti.md` |
| Extracción con IA | `docs/pb-01_extraccion_requisitos.md` |
| Modelo SAW | `docs/motor_de_reglas_puntaje_ponderado.md` |
| Implementación del motor, API y pantallas | `docs/pb-02_motor_de_decision.md` |
| Ideas fuera de alcance | `docs/ideas_futuras.md` |

---

## 14. Comandos para la presentación (PowerShell, uno por uno)

Todos desde la raíz del repositorio, salvo que se indique otra carpeta. **No muestres el
archivo `.env` en pantalla: contiene la clave de la IA.** Muestra `.env.example`.

### Antes de empezar

Terminal 1, backend:

```powershell
.\.venv\Scripts\Activate.ps1
```
```powershell
uvicorn app.main:app --app-dir backend --reload
```

Terminal 2, frontend:

```powershell
Set-Location frontend
```
```powershell
npm run dev
```

- Aplicación: http://localhost:5173
- Documentación interactiva de la API: http://localhost:8000/docs

Para empezar sin casos guardados (opcional, con el backend detenido o encendido):

```powershell
Remove-Item data\seci_ti.sqlite3
```

### 1. Demo de la aplicación

En el navegador, en http://localhost:5173: pegar el caso de la sección 9, analizar,
confirmar y recargar `/casos/<id>`. Luego abrir http://localhost:5173/casos.

### 2. El motor es determinístico y no depende de la IA

Calcula la recomendación enviando directamente las seis variables y el orden, sin llamar a
Gemini. Es el ejemplo numérico de la sección 6: debe dar **A = −0,2375, B = 1,6625,
C = 1,3250** y arquitectura B.

```powershell
$body = @'
{
  "business_case": "Aplicación con picos de demanda predecibles y alta criticidad para el negocio.",
  "requirements": {
    "service_interruption_tolerance": {"value": "medium", "status": "detected", "evidence": ["interrupciones cortas"]},
    "business_continuity_criticality": {"value": "high", "status": "detected", "evidence": ["detiene las ventas"]},
    "information_sensitivity": {"value": "medium", "status": "detected", "evidence": ["información interna"]},
    "available_budget": {"value": "medium", "status": "detected", "evidence": ["presupuesto moderado"]},
    "demand_pattern": {"value": "predictable_peaks", "status": "detected", "evidence": ["campañas programadas"]},
    "expected_load_volume": {"value": "medium", "status": "detected", "evidence": ["carga media"]}
  },
  "additional_context": {},
  "priority_ranking": {"never_stop_working": 1, "fast_under_load": 2, "lowest_cost": 3, "protect_information": 4}
}
'@
```
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/cases -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

Ejecuta el segundo comando dos veces: mismos puntajes (reproducibilidad). Para ver el efecto
del ranking, vuelve a enviar el mismo cuerpo con `"priority_ranking": {}` y compara
(pesos iguales, otros totales).

### 3. Registro de casos

Listado de casos por la API:

```powershell
Invoke-RestMethod http://localhost:8000/api/cases | ConvertTo-Json -Depth 4
```

Lo que hay en la base SQLite (arquitectura, fecha y si hubo trade-off):

```powershell
python -c "import sqlite3; c = sqlite3.connect('data/seci_ti.sqlite3'); [print(r) for r in c.execute('select id, created_at, architecture, trade_off from cases')]"
```

### 4. Pruebas

Backend (desde `backend`):

```powershell
Set-Location backend
```
```powershell
pytest
```
```powershell
ruff check .
```

Solo el motor, con detalle (para mostrar qué se prueba):

```powershell
pytest tests/test_weights.py tests/test_scoring.py tests/test_selection.py tests/test_engine.py -v
```

Frontend (desde `frontend`):

```powershell
Set-Location ..\frontend
```
```powershell
npm test
```
```powershell
npm run lint
```
```powershell
npm run build
```

### 5. Lo que viene (mostrar que está planeado)

```powershell
Get-ChildItem infrastructure -Recurse
```

Carpetas `architecture-a`, `architecture-b` y `architecture-c`, listas para las plantillas
CloudFormation.
