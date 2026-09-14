# Síntesis de Pilares Well-Architected (AWS, Azure, GCP) para el Motor de Reglas de SECI-TI

## 1. Propósito de este documento

Este documento consolida en un **modelo único de pilares** las guías de buenas prácticas de infraestructura publicadas por los tres proveedores cloud líderes: AWS Well-Architected Framework, Azure Well-Architected Framework y Google Cloud Well-Architected Framework.

El objetivo no es replicar ninguno de los tres frameworks completos, sino **extraer el núcleo común** que es directamente aplicable a la decisión que debe tomar el motor de reglas de SECI-TI: *dado un contexto de negocio, ¿qué características de infraestructura se requieren, y cuál de las tres arquitecturas del catálogo (A: básica, B: escalable, C: resiliente) las satisface mejor?*

Por esta razón, el documento se enfoca únicamente en los **cuatro pilares convergentes** entre los tres proveedores: **Reliability (Confiabilidad), Security (Seguridad), Cost Optimization (Optimización de costos)** y **Performance Efficiency (Eficiencia de rendimiento)**. Los pilares de *Operational Excellence* y *Sustainability*, aunque presentes en los tres frameworks, no se desarrollan aquí — ver justificación en la sección 6.

---

## 2. Metodología de síntesis

Para cada pilar unificado se presenta:

1. **Definición sintetizada**: una definición única que refleja el consenso entre los tres proveedores (no la definición literal de ninguno, sino su punto en común).
2. **Criterios convergentes**: preocupaciones que los tres frameworks tratan de forma equivalente, aunque con nombres o énfasis distintos.
3. **Matices divergentes**: dónde un proveedor pone más énfasis que los otros, y si eso es relevante o no para SECI-TI.
4. **Traducción a variable del motor de reglas**: cómo este pilar se convierte en una variable de entrada concreta y medible dentro de tu formulario/extractor NLU.

---

## 3. Pilar unificado: RELIABILITY (Confiabilidad / Fiabilidad)

**Definición sintetizada:** capacidad de un sistema para cumplir su función correctamente y de forma consistente, incluyendo su habilidad de resistir fallos, recuperarse de ellos y mantener continuidad operativa durante todo su ciclo de vida.

**Criterios convergentes en los tres proveedores:**
- Definición explícita de objetivos de recuperación: tiempo tolerable de interrupción (RTO) y punto de recuperación aceptable en términos de pérdida de datos (RPO).
- Diseño para tolerancia a fallos: eliminar puntos únicos de falla, distribuir componentes críticos.
- Recuperación automática ante fallos (self-healing) y capacidad de escalar horizontalmente como mecanismo de resiliencia.
- Pruebas del comportamiento ante fallos (chaos engineering / simulación de fallos) como práctica recomendada.
- Monitoreo y observación continua como precondición para detectar y responder a problemas de confiabilidad.

**Matices divergentes:**
- AWS y GCP enfatizan explícitamente la definición de RTO/RPO como paso metodológico inicial obligatorio.
- GCP incorpora el concepto de "degradación elegante" (graceful degradation): el sistema puede perder precisión/rendimiento antes de fallar por completo, en vez de caerse abruptamente.
- Azure integra la confiabilidad más directamente con el diseño para "resiliencia y recuperación" como uno de sus objetivos de negocio explícitos.

Estos matices no son mutuamente excluyentes — son válidos para cualquiera de las tres arquitecturas de tu catálogo y no requieren tratamiento diferenciado.

**Traducción a variable del motor de reglas:**
> **Variable: Tolerancia a interrupción del servicio**
> Niveles sugeridos: *Alta tolerancia (horas aceptables) / Tolerancia media (minutos) / Tolerancia casi nula (continuidad crítica)*
> Relación con el catálogo: tolerancia alta → favorece Arquitectura A; tolerancia casi nula → favorece Arquitectura C (multi-AZ).

> **Variable secundaria: Criticidad de continuidad del negocio**
> Niveles sugeridos: *Baja / Media / Alta (impacto de una caída sobre la operación)*

---

## 4. Pilar unificado: SECURITY (Seguridad, Privacidad y Cumplimiento)

**Definición sintetizada:** capacidad de proteger la confidencialidad, integridad y disponibilidad de los datos y sistemas, mediante gestión de identidad y acceso, protección de datos, y alineación con requisitos regulatorios.

**Criterios convergentes:**
- Gestión de identidad y control de acceso (principio de mínimo privilegio) como base común.
- Protección de datos en tránsito y en reposo.
- Alineación con requisitos regulatorios y de cumplimiento como motivador explícito de decisiones de arquitectura.
- Detección y respuesta ante incidentes de seguridad.

**Matices divergentes:**
- GCP integra explícitamente "privacidad y cumplimiento" dentro del nombre mismo del pilar, dándole mayor peso relativo a requisitos regulatorios sectoriales (ej. su perspectiva específica para servicios financieros).
- AWS y Azure tratan la seguridad como un pilar más autocontenido, con menos acoplamiento explícito a marcos regulatorios sectoriales dentro del pilar mismo.

**Relevancia para SECI-TI:** dado que tu catálogo de arquitecturas (A/B/C) no varía significativamente en mecanismos de seguridad (todas asumen el mismo modelo de responsabilidad compartida de AWS Academy Learner Lab, con IAM restringido), este pilar tiene **menor capacidad de diferenciar entre arquitecturas** que Reliability o Cost. Su función principal en tu motor de reglas es más bien **informativa/de alerta** que decisoria.

**Traducción a variable del motor de reglas:**
> **Variable: Sensibilidad de la información manejada**
> Niveles sugeridos: *Baja / Media / Alta*
> Uso: no determina la arquitectura por sí sola, pero se usa para generar advertencias complementarias (ej. "considere cifrado adicional" o "revise si su sector tiene requisitos regulatorios de residencia de datos") independientemente de qué arquitectura se seleccione.

---

## 5. Pilar unificado: COST OPTIMIZATION (Optimización de costos)

**Definición sintetizada:** capacidad de un sistema para entregar el valor de negocio esperado al menor costo posible, evitando tanto el sobre-aprovisionamiento como el riesgo de sub-aprovisionamiento.

**Criterios convergentes:**
- Alinear el gasto en infraestructura con el valor de negocio generado (no gastar más de lo que la necesidad justifica).
- Aprovisionar solo los recursos necesarios y pagar solo por lo que se consume.
- Monitoreo continuo del gasto como práctica recomendada, no una decisión de una sola vez.
- Los tres frameworks son explícitos en que costo es un pilar en **tensión constante** con los demás (especialmente con Reliability y Performance): más disponibilidad y más rendimiento casi siempre implican más costo.

**Matices divergentes:**
- AWS distingue entre gestión financiera de la nube (cultura organizacional) y optimización técnica de recursos como dos focos separados dentro del pilar.
- GCP enmarca el costo explícitamente en términos de "modelo de costos cloud vs. on-premises" (CapEx vs. OpEx), lo cual es más una consideración de adopción que de arquitectura técnica.

**Relevancia para SECI-TI:** este es el pilar que **genera el conflicto central** que ya identificaron ustedes mismos (alta disponibilidad + bajo presupuesto). Los tres frameworks confirman que este trade-off no es un error de diseño sino una tensión estructural esperada — lo cual valida tu decisión de resolverlo con un sistema de puntaje ponderado que muestre el trade-off, en vez de una regla rígida.

**Traducción a variable del motor de reglas:**
> **Variable: Prioridad de costo**
> Niveles sugeridos: *Costo es prioridad sobre disponibilidad / Balance entre costo y disponibilidad / Disponibilidad es prioridad sobre costo*
> Esta es la variable que debe activar el mensaje de trade-off cuando entra en conflicto con Reliability.

---

## 6. Pilar unificado: PERFORMANCE EFFICIENCY (Eficiencia de rendimiento)

**Definición sintetizada:** capacidad de un sistema para usar los recursos computacionales de forma eficiente en relación con la demanda real, y de adaptar esa asignación de recursos a medida que la demanda cambia.

**Criterios convergentes:**
- Enfoque basado en datos: medir el comportamiento real de la carga antes de decidir capacidad.
- Elasticidad: capacidad de escalar hacia arriba o abajo según la demanda, en vez de aprovisionar para el pico máximo de forma permanente.
- Revisión periódica de la arquitectura de rendimiento, no una decisión estática de una sola vez.

**Matices divergentes:**
- AWS y GCP enfatizan la relación entre rendimiento y experiencia de usuario/negocio (menor tiempo de respuesta → mayor retención/ingreso) como justificación de negocio del pilar.
- Azure lo asocia más directamente con pruebas de carga tempranas y frecuentes como práctica operativa concreta — lo cual conecta directamente con tu componente de k6.

**Traducción a variable del motor de reglas:**
> **Variable: Patrón de demanda**
> Niveles sugeridos: *Constante y predecible / Con picos predecibles (estacional, por horario) / Con picos impredecibles*
> Relación con el catálogo: constante y bajo volumen → Arquitectura A; picos (predecibles o no) → Arquitectura B o C según se combine con Reliability.

> **Variable: Volumen esperado de carga**
> Niveles sugeridos: *Bajo / Medio / Alto*

---

## 7. Justificación de exclusión: Operational Excellence y Sustainability

Ambos pilares existen en los tres frameworks, pero se excluyen deliberadamente de este modelo de reglas por las siguientes razones:

- **Operational Excellence** trata procesos organizacionales (automatización de despliegues, prácticas DevOps, observabilidad operativa, gestión de incidentes). Tu catálogo de arquitecturas ya incorpora IaC y CloudWatch de forma uniforme en las tres alternativas — es decir, el nivel de "excelencia operacional" no varía entre Arquitectura A, B o C, por lo que no puede usarse como criterio para diferenciar entre ellas.
- **Sustainability** se enfoca en impacto ambiental y eficiencia energética. Ninguna de tus tres arquitecturas (todas basadas en EC2 + ALB + ASG dentro del mismo entorno de AWS Academy Learner Lab) ofrece una diferenciación significativa en este aspecto que pueda medirse o accionarse dentro del alcance de tu Capstone.

Ambos pilares pueden mencionarse en el marco teórico del proyecto como parte de la revisión de literatura, pero no deben convertirse en variables del motor de reglas.

---

## 8. Modelo consolidado de variables (resultado final de la síntesis)

| # | Variable | Pilar de origen | Niveles |
|---|---|---|---|
| 1 | Tolerancia a interrupción del servicio | Reliability | Alta / Media / Casi nula |
| 2 | Criticidad de continuidad del negocio | Reliability | Baja / Media / Alta |
| 3 | Sensibilidad de la información | Security | Baja / Media / Alta |
| 4 | Prioridad de costo | Cost Optimization | Costo prioritario / Balance / Disponibilidad prioritaria |
| 5 | Patrón de demanda | Performance Efficiency | Constante / Picos predecibles / Picos impredecibles |
| 6 | Volumen esperado de carga | Performance Efficiency | Bajo / Medio / Alto |

Estas 6 variables, con un máximo de 3 niveles cada una, son la base recomendada para la tabla de puntaje ponderado del motor de reglas.

---

## 9. Fuentes consultadas

**AWS Well-Architected Framework**
- Pilares (overview): https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html
- Reliability: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html
- Security: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html
- Cost Optimization: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
- Performance Efficiency: https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html

**Azure Well-Architected Framework**
- Pilares (overview): https://learn.microsoft.com/en-us/azure/well-architected/pillars
- Reliability: https://learn.microsoft.com/en-us/azure/well-architected/reliability/
- Security: https://learn.microsoft.com/en-us/azure/well-architected/security/
- Cost Optimization: https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/
- Performance Efficiency: https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/

**Google Cloud Well-Architected Framework**
- Pilares (overview): https://docs.cloud.google.com/architecture/framework
- Reliability: https://docs.cloud.google.com/architecture/framework/reliability
- Security, Privacy and Compliance: https://docs.cloud.google.com/architecture/framework/security
- Cost Optimization: https://docs.cloud.google.com/architecture/framework/cost-optimization
- Performance Optimization: https://docs.cloud.google.com/architecture/framework/performance-optimization

*Nota: las URLs de Azure para los pilares individuales (reliability/, security/, cost-optimization/, performance-efficiency/) se infieren del patrón de URL confirmado en la documentación oficial; verificar acceso directo antes de citarlas en el documento final del proyecto.*

---

## 10. Próximo paso sugerido

Con este modelo de 6 variables, el siguiente trabajo de diseño es construir la **tabla de puntaje ponderado** que asigna, para cada combinación de niveles, cuántos puntos suma cada una de las tres arquitecturas (A/B/C) — incluyendo la lógica de detección de conflicto (ej. variable 4 = "costo prioritario" pero variables 1-2 apuntan fuertemente a Arquitectura C) que dispara el mensaje de trade-off.
