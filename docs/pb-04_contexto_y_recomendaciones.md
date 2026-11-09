# PB-04: contexto de plataformas y recomendaciones ampliadas

## Alcance

Admite casos de plataformas nuevas y existentes. La descripcion del negocio se
mantiene separada del texto de la arquitectura actual. El motor determinista
continua seleccionando A/B/C con las seis variables y prioridades confirmadas.
Un asesor de IA independiente amplia el resultado con alternativas y mejoras
de arquitectura, aplicacion, datos, seguridad, continuidad, rendimiento,
operacion y costos.

La aplicacion de demostracion, las tres plantillas y la seleccion para despliegue
permanecen iguales. El informe no modifica recursos AWS, no genera IaC ni cambia
la recomendacion del motor. No se despliega codigo de la plataforma descrita.

## Entrada y revision

El nuevo contrato `ProjectContext` contiene:

| Campo | Valores y reglas |
| --- | --- |
| `scenario` | `new` o `existing`; predeterminado `new` |
| `current_architecture` | Texto de 10 a 20.000 caracteres tras limpiar espacios, obligatorio si es `existing` |

Una plataforma nueva no puede incluir una arquitectura existente. El caso de
negocio admite de 10 a 20.000 caracteres, independientemente del limite de la
arquitectura actual. Ambos se envian al extractor en campos separados, conservando
la descripcion original; no se concatena el JSON como si fuera el caso de negocio.

Los proveedores reciben una salida de extraccion que no incluye `project_context`.
El backend incorpora el contexto de la solicitud y conserva su autoridad sobre
esos datos. No puede ser sustituido por una reinterpretacion del modelo.

Los recursos actuales tampoco se convierten automaticamente en necesidades:
una VM no implica carga baja y tener replicas no demuestra criticidad alta.
La revision humana sigue permitiendo corregir los seis requisitos y las prioridades.

## Informe ampliado

Se solicita desde el detalle de un caso ya confirmado y guardado. No se genera
en un GET ni al confirmar: esto mantiene utilizable la recomendacion A/B/C aunque
el proveedor no este disponible y evita consumir tokens al abrir cada caso.

`POST /api/cases/{id}/advice` recibe `{"regenerate": false}` y devuelve:

- `generated_at`: fecha UTC del informe guardado.
- `provider` y `model`: configuracion que produjo el informe.
- `content.summary`: evaluacion general del caso.
- `content.current_architecture_assessment`: evaluacion de la descripcion actual,
  obligatoria para plataformas existentes y nula para nuevas.
- `content.recommendations`: mejoras con categoria, prioridad, esfuerzo, accion,
  justificacion, beneficio esperado, compromisos y evidencia del texto.
- `content.alternatives`: opciones fuera del catalogo con condiciones de uso,
  compromisos y pasos de adopcion o migracion.
- `content.next_steps`, `assumptions` y `open_questions`: plan, supuestos e
  informacion faltante.

La evidencia es contextual y declarada por el modelo, no telemetria ni verificacion
independiente. No se ejecutan instrucciones o URLs incluidas por el usuario.
Las alternativas son una seleccion contextual, no un inventario exhaustivo de
todos los productos ni una certificacion de cumplimiento o disponibilidad.

Si ya existe un informe, un POST normal devuelve el guardado. Regenerar requiere
`{"regenerate": true}`. Una falla del proveedor o de validacion conserva el ultimo
informe y la recomendacion A/B/C; una falla al guardar no se presenta como exito.
Una primera generacion concurrente inserta solo si no existe informe: una respuesta
lenta no puede sobrescribir una regeneracion que ya termino en otra sesion.
El endpoint devuelve 404 si no existe el caso, 422 para entrada invalida y 503
si el proveedor o el almacenamiento no permiten completar la operacion.

## Implementacion

- `schemas/project_context.py`: escenarios y descripcion actual.
- `schemas/architecture_advice.py`: entrada y salida tipadas del asesor.
- `ai/architecture_advisor.py`: implementaciones Gemini/OpenAI con el proveedor
  y modelo ya configurados, salidas estructuradas y validacion Pydantic.
- `ai/prompts/architecture_advisor.py`: instrucciones separadas de la extraccion.
- `services/architecture_advice_service.py`: caso, cache y regeneracion explicita.
- `api/architecture_advice.py`: entrada HTTP y errores publicos.
- `persistence/sqlite_repository.py`: almacenamiento transaccional del informe.

El contexto se guarda dentro de `confirmed_json`. El informe usa una tabla
`case_advice` relacionada por `case_id`, creada de forma aditiva al abrir la base.
No se elimina ni reescribe la tabla `cases`. Los registros antiguos sin contexto
usan `new` y sin descripcion actual, y los que no tienen informe devuelven
`advice: null`. El listado incluye `scenario` para reconocer ambos tipos de caso.

Para Gemini se conserva la forma cerrada del JSON y sus enumeraciones, pero se
omiten los limites de longitud y cantidad de elementos en el esquema enviado al
proveedor: la combinacion del esquema completo con esos limites produjo un
`400 INVALID_ARGUMENT` en la verificacion real. El prompt conserva los limites
y Pydantic los verifica al recibir el informe; esta adaptacion no permite guardar
resultados que excedan el contrato de SECI-TI. OpenAI mantiene su esquema tipado.

## Configuracion y verificacion

Se reutilizan `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` y `AI_TIMEOUT_SECONDS`.
Las credenciales permanecen en el backend. Generar o regenerar un informe requiere
acceso al proveedor y puede consumir su cuota; consultar uno guardado no lo hace.

Las pruebas normales usan clientes y asesores falsos. Cubren ambos escenarios,
persistencia, bases de datos antiguas, cache, regeneracion, fallos sin perdida de
datos, validacion de salidas y mantenimiento del flujo A/B/C y de la demo AWS.
No necesitan credenciales ni crean recursos.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -m "not integration"
.\.venv\Scripts\python.exe -m ruff check backend
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```
