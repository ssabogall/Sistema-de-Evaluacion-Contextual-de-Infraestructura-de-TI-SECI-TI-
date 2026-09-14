# Motor de Reglas SECI-TI: Modelo de Puntaje Ponderado

## 1. Resumen del modelo

El motor de reglas decide entre las tres arquitecturas del catálogo (A: básica, B: escalable, C: resiliente) usando un modelo de **suma ponderada (Simple Additive Weighting, SAW)**, técnica estándar de análisis de decisión multicriterio:

$$\text{Puntaje}(\text{arquitectura}) = \sum_{i=1}^{n} w_i \times s_i(\text{arquitectura})$$

- $s_i(\text{arquitectura})$: qué tan bien esa arquitectura satisface el nivel reportado de la variable $i$ (tabla de compatibilidad fija, definida por el equipo con base en la síntesis de pilares WAF).
- $w_i$: peso de importancia de cada pilar, **derivado del ranking de prioridades que el propio usuario define** para su caso de negocio (no hardcodeado).

Gana la arquitectura con mayor puntaje total. La diferencia entre el 1° y 2° lugar se usa para generar el mensaje de trade-off cuando corresponda.

---

## 2. Variables del modelo (versión corregida)

> **Cambio importante respecto a la versión anterior:** la variable "Prioridad de costo" se redefine como un **hecho objetivo** ("Presupuesto disponible"), separada de la **preferencia** de cuánto le importa el costo al usuario — esa preferencia ahora se captura en el ranking de la sección 4, no como variable de entrada duplicada.

| # | Variable | Tipo | Pilar de origen | Niveles |
|---|---|---|---|---|
| 1 | Tolerancia a interrupción del servicio | Hecho | Reliability | Alta / Media / Casi nula |
| 2 | Criticidad de continuidad del negocio | Hecho | Reliability | Baja / Media / Alta |
| 3 | Sensibilidad de la información | Hecho | Security | Baja / Media / Alta |
| 4 | **Presupuesto disponible** *(redefinida)* | Hecho | Cost Optimization | Bajo / Medio / Alto |
| 5 | Patrón de demanda | Hecho | Performance Efficiency | Constante / Picos predecibles / Picos impredecibles |
| 6 | Volumen esperado de carga | Hecho | Performance Efficiency | Bajo / Medio / Alto |

---

## 3. Tabla de compatibilidad (escala -2 a +3)

| Variable | Nivel | Arq. A | Arq. B | Arq. C |
|---|---|---|---|---|
| **Tolerancia a interrupción** | Alta | +3 | +1 | -1 |
| | Media | 0 | +2 | +1 |
| | Casi nula | -2 | 0 | +3 |
| **Criticidad de continuidad** | Baja | +2 | +1 | -1 |
| | Media | 0 | +2 | +1 |
| | Alta | -2 | +1 | +3 |
| **Sensibilidad de datos** | Baja | +1 | +1 | +1 |
| | Media | 0 | +1 | +1 |
| | Alta | -1 | 0 | +2 |
| **Presupuesto disponible** | Bajo | +3 | +1 | -2 |
| | Medio | +1 | +2 | +1 |
| | Alto | -1 | +1 | +3 |
| **Patrón de demanda** | Constante | +2 | 0 | 0 |
| | Picos predecibles | -1 | +2 | +1 |
| | Picos impredecibles | -2 | +1 | +2 |
| **Volumen de carga** | Bajo | +2 | 0 | -1 |
| | Medio | 0 | +2 | +1 |
| | Alto | -2 | +1 | +2 |

*(Nota: "Sensibilidad de datos" tiene poca capacidad discriminante porque las 3 arquitecturas comparten el mismo modelo de seguridad de AWS Academy Learner Lab. Esto es esperado, no un error.)*

---

## 4. Pesos configurables vía ranking de prioridades de negocio

**Problema evitado:** pedirle al usuario que reparta porcentajes entre "Reliability, Cost Optimization, Performance Efficiency, Security" viola el principio de no exponer conceptos técnicos. En su lugar, el usuario **ordena 4 afirmaciones de negocio** de más a menos importante para su caso:

1. *"Que la aplicación nunca deje de funcionar, incluso si eso cuesta más."* → Reliability
2. *"Mantener el costo de infraestructura lo más bajo posible."* → Cost Optimization
3. *"Que la aplicación responda rápido incluso en momentos de mucho tráfico."* → Performance Efficiency
4. *"Proteger al máximo la información que manejo."* → Security

Este ranking puede capturarse de forma natural dentro de la conversación con el módulo LLM de extracción NLU (ver documento de arquitectura de esa capa), sin necesidad de una pantalla técnica separada.

### 4.1 Fórmula de conversión ranking → pesos (PENDIENTE DE DECIDIR)

Dos opciones sobre la mesa, ambas técnicas estándar de "rank-order weighting":

**Opción A — Lineal simple (más fácil de justificar y explicar):**

| Rango | Peso |
|---|---|
| 1° | 40% |
| 2° | 30% |
| 3° | 20% |
| 4° | 10% |

**Opción B — Suavizada (evita que el pilar en último lugar quede casi anulado):**

| Rango | Peso |
|---|---|
| 1° | 32.5% |
| 2° | 27.5% |
| 3° | 22.5% |
| 4° | 17.5% |

**Consideración clave:** con la Opción A, un usuario que ordena "Presupuesto" en último lugar reduce su influencia a solo 10% — lo cual puede ser un problema si aun así tiene un presupuesto real y limitado que no debería ignorarse casi por completo. La Opción B preserva un peso mínimo relevante para cualquier pilar, incluso el menos prioritario.

**Decisión pendiente:** elegir A o B (o una tercera fórmula) antes de implementar — queda como punto a resolver con el equipo/profesor.

---

## 5. Ejemplo numérico completo

**Caso:** tolerancia media, criticidad alta, datos sensibles medio, presupuesto medio, demanda con picos predecibles, volumen medio.
**Ranking del usuario:** 1° Reliability, 2° Performance Efficiency, 3° Cost Optimization, 4° Security.
**Pesos aplicados (Opción A, lineal):** Reliability 40%, Performance 30%, Cost 20%, Security 10%.
**Nota:** como Reliability y Performance tienen 2 variables cada una, el peso del pilar se reparte entre sus variables (20% cada variable de Reliability, 15% cada variable de Performance).

```
Arq. A = 0.20(0) + 0.20(-2) + 0.10(0) + 0.20(1) + 0.15(-1) + 0.15(0)
       = 0 - 0.40 + 0 + 0.20 - 0.15 + 0 = -0.35

Arq. B = 0.20(2) + 0.20(1) + 0.10(1) + 0.20(2) + 0.15(2) + 0.15(2)
       = 0.40 + 0.20 + 0.10 + 0.40 + 0.30 + 0.30 = 1.70

Arq. C = 0.20(1) + 0.20(3) + 0.10(1) + 0.20(1) + 0.15(1) + 0.15(1)
       = 0.20 + 0.60 + 0.10 + 0.20 + 0.15 + 0.15 = 1.40
```

**Resultado: Arquitectura B gana (1.70 > 1.40 > -0.35).**

---

## 6. Mecanismo de detección de trade-off

Cuando el 1° y 2° lugar quedan cercanos (diferencia menor a un umbral a definir, ej. 20% del puntaje del ganador), el sistema genera un mensaje explicando qué variable favoreció a la opción no elegida. En el ejemplo anterior:

> *"Se seleccionó Arquitectura B. Arquitectura C quedó en segundo lugar, mejor posicionada en tolerancia a interrupción y criticidad de continuidad, pero con menor eficiencia de costo para el presupuesto reportado."*

Este mensaje sale de comparar directamente los puntajes por variable entre el 1° y 2° lugar — no requiere una regla adicional separada.

---

## 7. Distinción importante: métricas de decisión vs. métricas de validación

| | Métricas de decisión (este documento) | Métricas de validación experimental |
|---|---|---|
| Cuándo se usan | Antes del despliegue, para elegir arquitectura | Después del despliegue, para comprobar si la elección fue correcta |
| Origen | Definidas a priori por el equipo (tabla de compatibilidad + pesos) | Medidas empíricamente con k6 y CloudWatch |
| Ejemplos | Puntaje SAW, pesos por ranking | CPU%, latencia, requests/segundo, errores, actividad de Auto Scaling |

No deben mezclarse: la tabla de este documento no se valida con CloudWatch, se valida por revisión de criterio de ingeniería y coherencia con la síntesis de pilares WAF.

---

## 8. Próximos pasos

1. Decidir fórmula de conversión ranking → pesos (Opción A, B, u otra).
2. Definir el umbral de diferencia de puntaje que activa el mensaje de trade-off.
3. Validar la tabla de compatibilidad (sección 3) con Miguel y, si es posible, con el profesor — son juicios de ingeniería, no verdades absolutas.
4. Diseñar cómo el módulo LLM/NLU captura el ranking de las 4 afirmaciones de negocio dentro de la conversación con el usuario.
5. Implementar la función de puntaje en Python (tabla de compatibilidad + vector de pesos + fórmula SAW) como el núcleo del motor de reglas.

---

## Referencia relacionada

Este documento se apoya en la síntesis de pilares Well-Architected (AWS, Azure, GCP) documentada en `sintesis_pilares_waf_seci-ti.md`, donde se detalla el origen conceptual de cada una de las 6 variables.
