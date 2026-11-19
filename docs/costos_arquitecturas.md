# Costo estimado por arquitectura (RQ-09)

Estimación del costo por hora de operar cada arquitectura del catálogo, calculada
a partir de los recursos que crea cada plantilla de `infrastructure/` y de los
precios públicos de AWS **On-Demand en `us-east-1`** (la región por defecto en
`backend/app/config.py`), consultados en noviembre de 2026.

> Es una **estimación de lista de precios**, no un costo observado. AWS Academy
> Learner Lab descuenta de un crédito fijo y puede aplicar condiciones propias.
> Para validar las cifras, compare con el gasto que muestra el Learner Lab
> después de un despliegue de duración conocida.

## Precios unitarios usados

| Recurso | Precio | Fuente |
| --- | --- | --- |
| EC2 `t3.micro` (Linux) | 0,0104 USD/h | [Precios EC2 On-Demand](https://aws.amazon.com/ec2/pricing/on-demand/) |
| EC2 `t2.micro` (Linux, alternativa) | 0,0116 USD/h | [Precios EC2 On-Demand](https://aws.amazon.com/ec2/pricing/on-demand/) |
| EBS `gp3` | 0,08 USD/GB-mes → 8 GB ≈ 0,00088 USD/h | [Precios EBS](https://aws.amazon.com/ebs/pricing/) |
| IPv4 pública (instancia o nodo del ALB) | 0,005 USD/h por dirección | [Cargo de IPv4 pública](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/) |
| Monitoreo detallado EC2 (`Monitoring: true`) | ≈ 2,10 USD/instancia-mes (7 métricas × 0,30) → ≈ 0,00288 USD/h | [Precios CloudWatch](https://aws.amazon.com/cloudwatch/pricing/) |
| Application Load Balancer | 0,0225 USD/h + 0,008 USD por LCU-hora | [Precios ELB](https://aws.amazon.com/elasticloadbalancing/pricing/) |

Conversión mensual: 730 horas.

## Recursos que generan costo en cada plantilla

| Arquitectura | Instancias (inicial / mín / máx) | ALB | IPv4 públicas | Gratuitos (no suman) |
| --- | --- | --- | --- | --- |
| A | 1 / 1 / 1 | No | 1 (instancia) | VPC, subred, IGW, tablas de rutas, security group |
| B | 1 / 1 / 3 | Sí, en 2 AZ | 1 por instancia + 2 del ALB | Lo anterior + launch template, ASG, target group |
| C | 2 / 2 / 4 | Sí, en 2 AZ | 1 por instancia + 2 del ALB | Igual que B |

Costo por instancia `t3.micro` = EC2 + EBS 8 GB + IPv4 + monitoreo detallado
= 0,0104 + 0,00088 + 0,005 + 0,00288 ≈ **0,0192 USD/h**.

Costo fijo del ALB (B y C) = 0,0225 + 2 × 0,005 = **0,0325 USD/h**, más LCU según tráfico.

## Resultado (instancias `t3.micro`)

| Arquitectura | Escenario | USD/hora | USD/hora con 1 LCU de tráfico | USD/mes (730 h) sin LCU |
| --- | --- | --- | --- | --- |
| A | Única instancia | **0,0192** | — | 13,98 |
| B | Mínimo (1 instancia) | **0,0517** | 0,0597 | 37,71 |
| B | Máximo (3 instancias) | 0,0900 | 0,0980 | 65,67 |
| C | Mínimo (2 instancias) | **0,0708** | 0,0788 | 51,69 |
| C | Máximo (4 instancias) | 0,1091 | 0,1171 | 79,65 |

Con `t2.micro` cada instancia sube a ≈ 0,0204 USD/h. A queda en 0,0204, B mínimo
en 0,0529 y C mínimo en 0,0732 USD/h.

**Lectura:** en reposo, B cuesta unas 2,7 veces lo que A, y C unas 3,7 veces. El
mayor salto entre A y B no lo da el cómputo sino el ALB (0,0325 USD/h fijos), y
el paso de B a C lo da la segunda instancia permanente en otra zona. Esto
coincide con la tabla de compatibilidad del motor, que favorece a A cuando el
presupuesto es bajo y a C solo cuando es alto.

**Costo de un experimento:** tener las tres arquitecturas desplegadas a la vez
durante una hora, en su máximo y con 1 LCU, cuesta ≈ 0,0192 + 0,0980 + 0,1171
≈ **0,23 USD**. Si quedan encendidas un día completo por olvido, en su mínimo
cuestan ≈ 3,4 USD. Por eso el panel de despliegue exige confirmar el costo y
permite eliminar los stacks.

## Supuestos y riesgos de la estimación

- **Facturación por hora:** cada hora parcial del ALB se cobra completa. EC2 y
  el monitoreo detallado se prorratean.
- **Créditos T3:** las `t3` se lanzan en modo *unlimited*. Bajo carga sostenida
  por encima de la línea base (pruebas k6 largas) pueden cobrar 0,05 USD por
  vCPU-hora adicional. No está incluido en la tabla.
- **LCU:** en reposo el consumo de LCU es casi nulo. La columna "1 LCU" es una
  cota razonable para pruebas de carga cortas, no una medición.
- **No incluidos:** transferencia de datos de salida (los primeros GB del mes
  son gratuitos y la demo responde JSON pequeños), alarmas creadas por la
  política de *target tracking* (≈ 0,10 USD/mes cada una) y snapshots (las
  plantillas no crean ninguno).
- **Precios:** pueden cambiar. Verifique en las páginas oficiales antes de citar
  estas cifras, o recalcúlelas con la [AWS Pricing Calculator](https://calculator.aws/).

## Cómo verificarlo (método de RQ-09)

1. Desplegar una arquitectura desde el panel de SECI-TI y anotar la hora.
2. Con `describe_stacks` / `describe_instances` (boto3) confirmar el número de
   instancias en ejecución y el tipo de instancia.
3. Multiplicar por los precios de este documento y comparar contra el gasto que
   reporta el Learner Lab al eliminar el stack.
