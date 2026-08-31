# Requisitos del proyecto SECI-TI

Documento consolidado de requisitos, siguiendo la misma estructura de campos que la plantilla de Issue en `.github/ISSUE_TEMPLATE/requisito.md`. Cada requisito se presenta como un bloque `### [ID] Título`, con las mismas subsecciones que la plantilla (anidadas un nivel más para encajar dentro de las secciones del documento).

## Requisitos de Infraestructura (Validación experimental)

### [RQ-01] Rendimiento bajo carga de referencia

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **medir el tiempo de respuesta bajo carga de referencia**,
para **confirmar que la arquitectura responde dentro de límites aceptables antes de someterla a pruebas más exigentes**.

#### Descripción del requisito
Bajo carga de referencia (ej. 50 usuarios virtuales concurrentes), la aplicación debe responder dentro de un tiempo aceptable, aplicable a las Arquitecturas A, B y C.

#### Criterio de aceptación
- [ ] El percentil 95 (p95) del tiempo de respuesta HTTP es menor a 300 ms

#### Requisito de calidad asociado (RNF)
**Atributo:** Rendimiento
**Métrica:** p95 de http_req_duration
**Umbral objetivo:** p95 < 300 ms

#### Dependencias
Ninguna

#### Método de verificación
k6 (http_req_duration)

#### Responsable
Por definir

### [RQ-02] Escalabilidad ante rampa de carga

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **observar el comportamiento del sistema durante un incremento gradual de usuarios**,
para **verificar que las Arquitecturas B y C escalan correctamente**.

#### Descripción del requisito
Durante una rampa de carga de 10 a 200 usuarios virtuales en 5 minutos, el sistema debe seguir respondiendo dentro de límites aceptables (aplica a B y C).

#### Criterio de aceptación
- [ ] p95 del tiempo de respuesta menor a 500 ms
- [ ] Tasa de errores menor al 1%

#### Requisito de calidad asociado (RNF)
**Atributo:** Escalabilidad
**Métrica:** p95 de tiempo de respuesta + tasa de error
**Umbral objetivo:** p95 < 500 ms y errores < 1%

#### Dependencias
RQ-01

#### Método de verificación
k6 (perfil ramping-vus) + CloudWatch (CPUUtilization, RequestCount)

#### Responsable
Por definir

### [RQ-03] Reacción del Auto Scaling ante carga sostenida

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **confirmar que el Auto Scaling añade capacidad automáticamente**,
para **verificar que las Arquitecturas B y C se adaptan a incrementos de demanda sin intervención manual**.

#### Descripción del requisito
Ante un incremento de carga sostenido, el Auto Scaling debe reaccionar añadiendo capacidad (aplica a B y C).

#### Criterio de aceptación
- [ ] Existe una nueva instancia en estado InService dentro del umbral definido

#### Requisito de calidad asociado (RNF)
**Atributo:** Elasticidad
**Métrica:** Tiempo entre superar el umbral de CPU y tener una nueva instancia InService
**Umbral objetivo:** menor o igual a 5 minutos

#### Dependencias
RQ-02

#### Método de verificación
CloudWatch (alarmas de Auto Scaling, GroupInServiceInstances) correlacionado con timestamps de k6

#### Responsable
Por definir

### [RQ-04] Capacidad máxima sostenible

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **identificar el punto de quiebre de cada arquitectura**,
para **comparar objetivamente cuánta carga concurrente soporta cada una antes de degradarse**.

#### Descripción del requisito
Existe un punto máximo de usuarios concurrentes que la arquitectura puede sostener sin degradarse (aplica a A, B y C).

#### Criterio de aceptación
- [ ] Se identifica el número de VUs concurrentes antes de que la tasa de error supere 5% o el p95 supere 1 segundo

#### Requisito de calidad asociado (RNF)
**Atributo:** Capacidad
**Métrica:** N.º de VUs concurrentes en el punto de quiebre
**Umbral objetivo:** A ~20 VUs / B y C ~150 VUs (a calibrar con prueba base)

#### Dependencias
RQ-01

#### Método de verificación
k6 prueba de estrés incremental hasta punto de quiebre

#### Responsable
Por definir

### [RQ-05] Disponibilidad ante caída de una instancia

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **simular la caída de una instancia**,
para **confirmar que el servicio sigue disponible en las Arquitecturas B y C**.

#### Descripción del requisito
Ante la caída simulada de una instancia, el servicio debe seguir disponible (aplica a B y C).

#### Criterio de aceptación
- [ ] El porcentaje de solicitudes exitosas durante el incidente es mayor o igual a 99%

#### Requisito de calidad asociado (RNF)
**Atributo:** Disponibilidad
**Métrica:** % de solicitudes exitosas durante el incidente
**Umbral objetivo:** mayor o igual a 99%

#### Dependencias
RQ-03

#### Método de verificación
Terminar instancia vía boto3 durante prueba k6 activa + CloudWatch (HealthyHostCount)

#### Responsable
Por definir

### [RQ-06] Resiliencia ante caída de una zona de disponibilidad

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **simular la caída completa de una AZ**,
para **confirmar que la Arquitectura C mantiene el servicio con la AZ sobreviviente**.

#### Descripción del requisito
Ante la caída simulada de todas las instancias de una AZ, el tráfico debe seguir siendo atendido por la AZ sobreviviente (aplica solo a C).

#### Criterio de aceptación
- [ ] El porcentaje de solicitudes exitosas durante el incidente es mayor o igual a 95%

#### Requisito de calidad asociado (RNF)
**Atributo:** Resiliencia
**Métrica:** % de solicitudes exitosas durante el incidente
**Umbral objetivo:** mayor o igual a 95%

#### Dependencias
RQ-05

#### Método de verificación
boto3 (terminar instancias de una AZ) + CloudWatch (HealthyHostCount por AZ)

#### Responsable
Por definir

### [RQ-07] Recuperación de capacidad tras un fallo

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **medir el tiempo de recuperación tras perder una instancia**,
para **confirmar que las Arquitecturas B y C restablecen su capacidad en un tiempo razonable**.

#### Descripción del requisito
Tras la pérdida de una instancia, el sistema debe recuperar su capacidad completa en un tiempo razonable (aplica a B y C).

#### Criterio de aceptación
- [ ] El tiempo entre la caída y el restablecimiento de capacidad total es menor o igual a 6 minutos

#### Requisito de calidad asociado (RNF)
**Atributo:** Recuperación (RTO)
**Métrica:** Tiempo entre la caída y el restablecimiento de capacidad total
**Umbral objetivo:** menor o igual a 6 minutos

#### Dependencias
RQ-05

#### Método de verificación
CloudWatch + logs de eventos de Auto Scaling

#### Responsable
Por definir

### [RQ-08] Confiabilidad bajo carga sostenida

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **medir la tasa de errores durante una prueba sostenida**,
para **confirmar la confiabilidad de las tres arquitecturas bajo condiciones normales**.

#### Descripción del requisito
Durante una prueba sostenida de 10 minutos a carga de referencia, la tasa de errores debe mantenerse baja (aplica a A, B y C).

#### Criterio de aceptación
- [ ] El porcentaje de respuestas HTTP 5xx es menor a 1%

#### Requisito de calidad asociado (RNF)
**Atributo:** Confiabilidad
**Métrica:** % de respuestas HTTP 5xx
**Umbral objetivo:** menor a 1%

#### Dependencias
RQ-01

#### Método de verificación
k6 (http_req_failed) + CloudWatch (HTTPCode_Target_5XX_Count, solo B/C)

#### Responsable
Por definir

### [RQ-09] Eficiencia de costos

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo del proyecto**,
quiero **estimar el costo de cada arquitectura**,
para **asegurar que las pruebas se mantengan dentro del presupuesto del Learner Lab**.

#### Descripción del requisito
El costo de operar cada arquitectura debe mantenerse dentro del presupuesto del Learner Lab (aplica a A, B y C).

#### Criterio de aceptación
- [ ] Se documenta el costo estimado por hora de cada arquitectura desplegada

#### Requisito de calidad asociado (RNF)
**Atributo:** Eficiencia de costos
**Métrica:** Costo estimado por hora según recursos activos
**Umbral objetivo:** Pendiente de definir techo por arquitectura según presupuesto real del lab

#### Dependencias
Ninguna

#### Método de verificación
AWS Pricing Calculator + boto3 (describe_instances, describe_stacks)

#### Responsable
Por definir

### [RQ-10] Seguridad de exposición de puertos

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo del proyecto**,
quiero **verificar que no existan puertos administrativos expuestos a Internet**,
para **reducir el riesgo de acceso no autorizado en las tres arquitecturas**.

#### Descripción del requisito
La infraestructura no debe exponer puertos administrativos a Internet (aplica a A, B y C).

#### Criterio de aceptación
- [ ] El número de Security Groups con reglas de entrada 0.0.0.0/0 en puertos administrativos (ej. 22, 3389) es igual a cero

#### Requisito de calidad asociado (RNF)
**Atributo:** Seguridad
**Métrica:** N.º de Security Groups con reglas de entrada abiertas en puertos admin
**Umbral objetivo:** 0

#### Dependencias
Ninguna

#### Método de verificación
Revisión de la plantilla .yaml + boto3 (describe_security_groups)

#### Responsable
Por definir

### [RQ-11] Observabilidad de la infraestructura

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo de validación**,
quiero **asegurar que las métricas críticas estén disponibles en CloudWatch**,
para **poder correlacionar los resultados de k6 con el comportamiento interno de la infraestructura**.

#### Descripción del requisito
Debe existir visibilidad suficiente del comportamiento de la infraestructura durante las pruebas (aplica a A, B y C).

#### Criterio de aceptación
- [ ] El 100% de las métricas críticas definidas (CPU, latencia, errores, hosts saludables) están disponibles en CloudWatch tras el despliegue

#### Requisito de calidad asociado (RNF)
**Atributo:** Observabilidad
**Métrica:** N.º de métricas críticas disponibles en CloudWatch
**Umbral objetivo:** 100% de las métricas definidas disponibles

#### Dependencias
Ninguna

#### Método de verificación
Verificación del namespace de CloudWatch tras el despliegue

#### Responsable
Por definir

### [RQ-12] Reproducibilidad del despliegue

**Tipo:** No funcional
**Capa:** Infraestructura desplegada
**Sprint:** Por definir

#### Historia de usuario
Como **equipo del proyecto**,
quiero **que el despliegue de cada arquitectura sea consistente entre ejecuciones**,
para **poder repetir experimentos sin resultados contradictorios**.

#### Descripción del requisito
El despliegue de cada arquitectura debe ser reproducible y consistente (aplica a A, B y C).

#### Criterio de aceptación
- [ ] El stack alcanza CREATE_COMPLETE en menos o igual a 15 minutos
- [ ] 0 errores en 3 ejecuciones consecutivas del mismo despliegue

#### Requisito de calidad asociado (RNF)
**Atributo:** Mantenibilidad
**Métrica:** Tiempo de create-stack hasta CREATE_COMPLETE y consistencia entre ejecuciones
**Umbral objetivo:** menor o igual a 15 minutos, 0 errores en 3 ejecuciones consecutivas

#### Dependencias
Ninguna

#### Método de verificación
boto3 (describe_stacks, StackStatus) + timestamps

#### Responsable
Por definir

## Requisitos del Motor de Reglas

### [RF-01] Definición de variables del contexto de negocio

**Tipo:** Funcional (tarea del equipo)
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
Como **equipo del proyecto**,
quiero **identificar qué variables del contexto de negocio son relevantes**,
para **poder construir reglas de decisión fundamentadas**.

#### Descripción del requisito
Investigar y documentar qué variables del contexto de negocio (sector, criticidad, demanda, presupuesto, etc.) son relevantes para derivar necesidades de infraestructura, apoyándose en AWS Well-Architected e ISO/IEC 25010.

#### Criterio de aceptación
- [ ] Existe un documento con las variables seleccionadas y su justificación

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
Ninguna

#### Método de verificación
Documento de variables revisado por el equipo/asesor

#### Responsable
Por definir

### [RF-02] Definición de reglas de traducción

**Tipo:** Funcional (tarea del equipo)
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
Como **equipo del proyecto**,
quiero **definir reglas explícitas que traduzcan combinaciones de variables en necesidades de infraestructura**,
para **que el motor de reglas tenga una base determinista de decisión**.

#### Descripción del requisito
Definir el conjunto de reglas/condiciones que traducen combinaciones de variables en necesidades de infraestructura (ej. alta demanda + crecimiento impredecible implica necesidad de elasticidad).

#### Criterio de aceptación
- [ ] Existe un documento de reglas aprobado por el equipo/asesor

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-01

#### Método de verificación
Documento de reglas revisado y aprobado

#### Responsable
Por definir

### [RF-03] Identificación de necesidades a partir del contexto

**Tipo:** Funcional (sistema)
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
Como **usuario de negocio**,
quiero **que el sistema identifique mis necesidades de infraestructura a partir de la información que doy sobre mi negocio**,
para **no tener que conocer conceptos técnicos**.

#### Descripción del requisito
El motor de reglas debe recibir el contexto de negocio capturado por el formulario y producir una lista de necesidades de infraestructura identificadas.

#### Criterio de aceptación
- [ ] Dado un input de ejemplo, el sistema retorna la lista de necesidades esperada

#### Requisito de calidad asociado (RNF)
No aplica (ver RNF-01, RNF-02, RNF-03)

#### Dependencias
RF-01, RF-02

#### Método de verificación
Prueba unitaria (input de ejemplo, lista de necesidades esperada)

#### Responsable
Por definir

### [RF-04] Selección de arquitectura según necesidades identificadas

**Tipo:** Funcional (sistema)
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
Como **usuario de negocio sin conocimientos técnicos**,
quiero **recibir una arquitectura recomendada a partir de la información que di sobre mi negocio**,
para **no tener que saber qué es un Auto Scaling Group o un Load Balancer para tomar una buena decisión de infraestructura**.

#### Descripción del requisito
El motor de reglas debe mapear las necesidades identificadas a una arquitectura del catálogo (A, B o C) según criterios de aceptación definidos para cada una.

#### Criterio de aceptación
- [ ] Dado un contexto de negocio de ejemplo, el sistema retorna una única arquitectura
- [ ] La arquitectura retornada coincide con la esperada en el conjunto de casos de prueba curados

#### Requisito de calidad asociado (RNF)
**Atributo:** Precisión del motor
**Métrica:** % de casos de prueba curados donde la arquitectura seleccionada coincide con la esperada
**Umbral objetivo:** mayor o igual a 90%

#### Dependencias
RF-01, RF-02, RF-03

#### Método de verificación
Suite de pruebas automatizadas (15-20 casos de negocio con arquitectura esperada conocida)

#### Responsable
Por definir

### [RF-05] Trazabilidad de la decisión del motor

**Tipo:** Funcional (sistema)
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
Como **usuario de negocio**,
quiero **entender por qué se me recomendó una arquitectura específica**,
para **confiar en la decisión y poder cuestionarla si no tiene sentido para mi caso**.

#### Descripción del requisito
El motor de reglas debe registrar y explicar qué reglas se activaron para justificar la arquitectura seleccionada.

#### Criterio de aceptación
- [ ] Para cada caso evaluado existe un registro de las reglas activadas

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-04

#### Método de verificación
Inspección del log de decisión por caso de prueba

#### Responsable
Por definir

### [RNF-01] Precisión del motor de reglas

**Tipo:** No funcional
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
Dado un conjunto de casos de prueba curados por el equipo (15-20 casos claros), el motor debe seleccionar la arquitectura esperada en la mayoría de los casos.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Precisión
**Métrica:** % de aciertos sobre el set de casos curados
**Umbral objetivo:** mayor o igual a 90%

#### Dependencias
RF-03, RF-04

#### Método de verificación
Suite de pruebas automatizadas (input, output esperado)

#### Responsable
Por definir

### [RNF-02] Determinismo del motor de reglas

**Tipo:** No funcional
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
El mismo input debe producir siempre el mismo output, sin variabilidad entre ejecuciones.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Determinismo
**Métrica:** Consistencia de resultados entre ejecuciones repetidas
**Umbral objetivo:** 100% de coincidencia en 5+ ejecuciones del mismo caso

#### Dependencias
RF-04

#### Método de verificación
Ejecutar el mismo caso 5 o más veces y comparar resultados

#### Responsable
Por definir

### [RNF-03] Tiempo de respuesta del motor de reglas

**Tipo:** No funcional
**Capa:** Motor de reglas
**Sprint:** Por definir

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
La evaluación de un caso no debe tardar más de un tiempo razonable, sin depender de llamadas externas lentas.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Rendimiento (tiempo de respuesta)
**Métrica:** Tiempo de ejecución por evaluación
**Umbral objetivo:** A definir tras prueba base (orden de segundos, no minutos)

#### Dependencias
RF-03, RF-04

#### Método de verificación
Medición de tiempo de ejecución en pruebas

#### Responsable
Por definir

> **Nota de alcance:** los requisitos de análisis de infraestructura existente se movieron a `ideas_futuras.md`.


## Requisitos de la Aplicación Web

### [RF-12] Diseño de preguntas del formulario

**Tipo:** Funcional (tarea del equipo)
**Capa:** Aplicación web
**Sprint:** Por definir

#### Historia de usuario
Como **usuario de negocio sin conocimientos técnicos**,
quiero **que las preguntas del formulario estén en un lenguaje que entienda**,
para **poder describir mi negocio sin necesidad de saber de infraestructura**.

#### Descripción del requisito
Diseñar las preguntas del formulario de contexto de negocio, redactadas en lenguaje no técnico, validadas contra las variables definidas en RF-01.

#### Criterio de aceptación
- [ ] Una persona ajena al proyecto comprende y responde el formulario sin ayuda técnica

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-01

#### Método de verificación
Revisión de preguntas por alguien ajeno al proyecto (prueba de comprensión)

#### Responsable
Por definir

### [RF-13] Envío del formulario al motor de reglas

**Tipo:** Funcional (sistema)
**Capa:** Aplicación web
**Sprint:** Por definir

#### Historia de usuario
Como **usuario de negocio**,
quiero **completar un formulario sobre mi negocio y enviarlo**,
para **recibir una recomendación de infraestructura**.

#### Descripción del requisito
La aplicación debe permitir al usuario completar el formulario de contexto de negocio y enviarlo al motor de reglas.

#### Criterio de aceptación
- [ ] El usuario puede completar y enviar el formulario, y el sistema recibe el contexto correctamente

#### Requisito de calidad asociado (RNF)
No aplica (ver RNF-07)

#### Dependencias
RF-12, RF-03

#### Método de verificación
Prueba funcional del flujo de formulario

#### Responsable
Por definir

### [RF-14] Presentación de la arquitectura recomendada

**Tipo:** Funcional (sistema)
**Capa:** Aplicación web
**Sprint:** Por definir

#### Historia de usuario
Como **usuario de negocio**,
quiero **ver la arquitectura recomendada junto con una explicación clara de por qué se eligió**,
para **confiar en la recomendación recibida**.

#### Descripción del requisito
La aplicación debe mostrar al usuario la arquitectura recomendada junto con una explicación comprensible de por qué fue seleccionada, usando la trazabilidad de RF-05.

#### Criterio de aceptación
- [ ] La explicación mostrada corresponde a las reglas activadas para ese caso

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-04, RF-05

#### Método de verificación
Revisión de que la explicación mostrada corresponda a las reglas activadas

#### Responsable
Por definir


### [RF-16] Presentación de resultados de validación

**Tipo:** Funcional (sistema)
**Capa:** Aplicación web
**Sprint:** Por definir

#### Historia de usuario
Como **usuario del sistema**,
quiero **ver los resultados de las pruebas de validación de forma clara**,
para **entender el comportamiento de la infraestructura sin tener que leer logs técnicos**.

#### Descripción del requisito
La aplicación debe presentar los resultados de las pruebas de validación (k6 + CloudWatch) de forma legible para el usuario, no como JSON o logs crudos.

#### Criterio de aceptación
- [ ] La vista de resultados refleja correctamente los datos crudos de origen, en formato legible

#### Requisito de calidad asociado (RNF)
No aplica (ver RQ-01 a RQ-12)

#### Dependencias
RQ-01 a RQ-12

#### Método de verificación
Revisión de la vista de resultados contra los datos crudos de origen

#### Responsable
Por definir

### [RNF-07] Usabilidad del formulario

**Tipo:** No funcional
**Capa:** Aplicación web
**Sprint:** Por definir

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
Un usuario sin conocimientos técnicos debe poder completar el formulario sin necesidad de ayuda externa.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Usabilidad
**Métrica:** Tiempo de finalización del formulario sin asistencia
**Umbral objetivo:** A definir tras prueba de usuario (orden de minutos)

#### Dependencias
RF-13

#### Método de verificación
Prueba de usuario con 2-3 personas ajenas al equipo, cronometrada

#### Responsable
Por definir

### [RNF-08] Tiempo de respuesta de la interfaz

**Tipo:** No funcional
**Capa:** Aplicación web
**Sprint:** Por definir

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
Las páginas principales de la aplicación deben cargar en un tiempo razonable en condiciones normales.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Rendimiento (tiempo de respuesta)
**Métrica:** Tiempo de carga de página
**Umbral objetivo:** A definir tras prueba base (orden de segundos)

#### Dependencias
RF-13, RF-14, RF-16

#### Método de verificación
Medición con herramientas de desarrollador del navegador o Lighthouse

#### Responsable
Por definir
