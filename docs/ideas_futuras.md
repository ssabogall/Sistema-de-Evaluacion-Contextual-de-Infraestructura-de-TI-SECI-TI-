# Ideas futuras / fuera de alcance del Capstone actual

Este documento reúne requisitos que el equipo consideró durante la etapa de
diseño, pero que **no forman parte del alcance del Capstone actual**
(Sprint 0, Sistema-de-Evaluación-Contextual-de-Infraestructura-de-TI-SECI-TI-).

El foco del semestre es la infraestructura desde cero: motor de reglas de
selección (caso de negocio → arquitectura A/B/C), despliegue vía IaC, y
validación experimental con k6 + CloudWatch (ver `requisitos.md`).

Los requisitos aquí listados corresponden al escenario de **análisis de
infraestructura existente** (parsear IaC de terceros, construir un modelo
interno, compararlo contra requisitos y reportar brechas). Se decidió
posponerlos porque:

- No tienen ninguna dependencia funcional con los RQ-01 a RQ-12 de
  validación experimental, que ya cubren el flujo principal del proyecto.
- Añadirían un tercer frente de trabajo completo (parser de IaC +
  resolución de dependencias + comparación de modelos) para un equipo de
  dos personas, sin espacio asignado en el plan de sprints del Sprint 0.
- El documento Sprint 0 oficial (entregado) no los menciona en su alcance,
  objetivos específicos, ni plan de fases — incluirlos como requisitos
  activos generaría una desviación de alcance no declarada.

Si en una fase posterior del proyecto (o como trabajo futuro fuera del
semestre) se decide retomar este escenario, este documento sirve como punto
de partida: los requisitos ya están redactados con la misma estructura que
`requisitos.md`, listos para reactivarse.

---

## Requisitos de Análisis de IaC

### [RF-06] Delimitación del alcance del parser

**Tipo:** Funcional (tarea del equipo)
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **equipo del proyecto**,
quiero **definir qué tipos de recursos de CloudFormation se van a soportar**,
para **no intentar cubrir un alcance inviable en el tiempo disponible**.

#### Descripción del requisito
Leer y delimitar qué tipos de recursos de CloudFormation se soportarán inicialmente (ej. solo VPC, EC2, ALB, Auto Scaling Group) antes de programar el parser.

#### Criterio de aceptación
- [ ] Existe un documento de alcance que indica qué recursos sí y qué recursos no se soportan

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
Ninguna

#### Método de verificación
Documento de alcance del parser

#### Responsable
Por definir

### [RF-07] Extracción de recursos desde archivos IaC

**Tipo:** Funcional (sistema)
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **usuario técnico**,
quiero **que el sistema lea mis archivos de CloudFormation**,
para **no tener que transcribir manualmente los recursos que definí**.

#### Descripción del requisito
El sistema debe leer y parsear uno o más archivos .yaml de CloudFormation y extraer los recursos definidos.

#### Criterio de aceptación
- [ ] Dado un set de plantillas de ejemplo (incluyendo A, B y C), el sistema extrae correctamente los recursos definidos en cada una

#### Requisito de calidad asociado (RNF)
No aplica (ver RNF-04)

#### Dependencias
RF-06

#### Método de verificación
Prueba con set de plantillas de ejemplo

#### Responsable
Por definir

### [RF-08] Identificación de dependencias entre recursos

**Tipo:** Funcional (sistema)
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **usuario técnico**,
quiero **que el sistema identifique cómo se relacionan mis recursos entre sí**,
para **tener un modelo real de mi infraestructura y no solo una lista plana de componentes**.

#### Descripción del requisito
El sistema debe identificar relaciones y dependencias explícitas entre recursos (ej. una instancia pertenece a una VPC, un ALB apunta a un Auto Scaling Group).

#### Criterio de aceptación
- [ ] Dado un caso con dependencias conocidas, el sistema las detecta correctamente

#### Requisito de calidad asociado (RNF)
No aplica (ver RNF-05)

#### Dependencias
RF-07

#### Método de verificación
Prueba con casos donde las dependencias esperadas se conocen de antemano

#### Responsable
Por definir

### [RF-09] Construcción de un modelo interno unificado

**Tipo:** Funcional (sistema)
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **usuario técnico**,
quiero **que el sistema combine múltiples archivos relacionados en un solo modelo**,
para **poder analizar infraestructuras distribuidas en varios manifiestos**.

#### Descripción del requisito
El sistema debe construir un modelo interno único de la infraestructura a partir de múltiples archivos relacionados.

#### Criterio de aceptación
- [ ] Dado un conjunto de N archivos relacionados, el sistema produce un único modelo consistente

#### Requisito de calidad asociado (RNF)
No aplica (ver RNF-06)

#### Dependencias
RF-08

#### Método de verificación
Prueba con un conjunto de archivos de ejemplo

#### Responsable
Por definir

### [RF-10] Comparación del modelo contra los requisitos identificados

**Tipo:** Funcional (sistema)
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **usuario técnico**,
quiero **saber si mi infraestructura actual cumple con los requisitos identificados para mi caso de negocio**,
para **saber si necesito hacer cambios**.

#### Descripción del requisito
El sistema debe comparar el modelo construido contra los requisitos/necesidades identificadas (salida del motor de reglas) y reportar cumplimiento o incumplimiento por criterio.

#### Criterio de aceptación
- [ ] Dado un caso con cumplimiento parcial conocido, el reporte refleja correctamente qué se cumple y qué no

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-09, RF-04

#### Método de verificación
Prueba con infraestructura conocida que cumple parcialmente

#### Responsable
Por definir

### [RF-11] Reporte de brechas y riesgos

**Tipo:** Funcional (sistema)
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **usuario técnico**,
quiero **un reporte claro de qué falta, qué sobra y qué riesgos existen en mi infraestructura**,
para **poder priorizar qué corregir primero**.

#### Descripción del requisito
El sistema debe generar un reporte de brechas que indique qué falta, qué sobra (sobre-provisión) y qué riesgos existen respecto a los requisitos.

#### Criterio de aceptación
- [ ] El reporte generado coincide con lo esperado para un caso de prueba conocido

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-10

#### Método de verificación
Revisión manual del reporte contra un caso de prueba conocido

#### Responsable
Por definir

### [RNF-04] Cobertura del parser de IaC

**Tipo:** No funcional
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
El parser debe procesar correctamente todos los recursos soportados según el alcance definido, sin fallar ante archivos válidos.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Cobertura
**Métrica:** % de recursos soportados procesados correctamente
**Umbral objetivo:** 100% de los recursos dentro del alcance definido

#### Dependencias
RF-07

#### Método de verificación
Suite de plantillas de prueba, incluyendo casos límite

#### Responsable
Por definir

### [RNF-05] Precisión en detección de dependencias

**Tipo:** No funcional
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
El sistema debe detectar correctamente la mayoría de las relaciones explícitas presentes en los casos de prueba curados.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Precisión
**Métrica:** % de dependencias detectadas correctamente
**Umbral objetivo:** mayor o igual a 95%

#### Dependencias
RF-08

#### Método de verificación
Comparación contra un mapa de dependencias esperado, definido manualmente

#### Responsable
Por definir

### [RNF-06] Escalabilidad del análisis de IaC

**Tipo:** No funcional
**Capa:** Análisis de IaC
**Sprint:** Fuera de alcance actual

#### Historia de usuario
No aplica (requisito no funcional transversal)

#### Descripción del requisito
El sistema debe poder procesar un número considerable de archivos/recursos sin fallar y en un tiempo razonable.

#### Criterio de aceptación
No aplica (ver umbral objetivo en Requisito de calidad asociado)

#### Requisito de calidad asociado (RNF)
**Atributo:** Escalabilidad
**Métrica:** Tiempo de procesamiento para un conjunto grande de archivos
**Umbral objetivo:** A definir tras prueba base, usando como referencia un escenario de decenas de manifiestos

#### Dependencias
RF-09

#### Método de verificación
Prueba de carga con un conjunto grande de archivos sintéticos

#### Responsable
Por definir

---

## Requisitos de la Aplicación Web (relacionados con análisis de IaC)

### [RF-15] Carga de archivos de IaC existente

**Tipo:** Funcional (sistema)
**Capa:** Aplicación web
**Sprint:** Fuera de alcance actual

#### Historia de usuario
Como **usuario técnico**,
quiero **cargar mis archivos de infraestructura existente**,
para **que el sistema los analice contra mis requisitos**.

#### Descripción del requisito
La aplicación debe permitir cargar uno o más archivos de IaC existentes para el escenario de análisis de infraestructura existente.

#### Criterio de aceptación
- [ ] El usuario puede cargar uno o más archivos y el sistema confirma su recepción

#### Requisito de calidad asociado (RNF)
No aplica (requisito funcional)

#### Dependencias
RF-07

#### Método de verificación
Prueba de carga de archivo(s) y confirmación de recepción

#### Responsable
Por definir
