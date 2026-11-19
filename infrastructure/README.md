# Infraestructura de laboratorio

Catalogo CloudFormation independiente por arquitectura. Las plantillas usan
exclusivamente funciones YAML en sintaxis larga (`Ref`, `Fn::Sub`, `Fn::GetAtt`,
etc.), compatibles con `yaml.safe_load`, sin macros, includes ni stacks anidados.
Implementan la base experimental de [RQ-01 a RQ-12](../docs/requisitos.md);
los umbrales de rendimiento, disponibilidad, costo y tiempo requieren mediciones
reales. No se consideran demostrados por las pruebas estructurales.

| Arquitectura | Entrada HTTP | Computo | Capacidad inicial / minima / maxima |
| --- | --- | --- | --- |
| [A](architecture-a/README.md) | IP publica EC2 | Una instancia, una AZ | 1 / 1 / 1 |
| [B](architecture-b/README.md) | ALB en dos AZ | ASG en una sola AZ | 1 / 1 / 3 |
| [C](architecture-c/README.md) | ALB en dos AZ | ASG en dos AZ | 2 / 2 / 4 |

## Contrato del backend

Rutas desde la raiz: `infrastructure/architecture-a/template.yaml`,
`infrastructure/architecture-b/template.yaml`,
`infrastructure/architecture-c/template.yaml`.

| Parametro | Tipo | Valor predeterminado |
| --- | --- | --- |
| `InstanceType` | String, `t2.micro` o `t3.micro` | `t3.micro` |
| `CaseId` | String de 1 a 256 caracteres | Obligatorio |
| `LatestAmiId` | `AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>` | `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64` |

El backend envia **solo `InstanceType` y `CaseId`**. CloudFormation resuelve el
parametro publico SSM para AL2023 x86_64. No requiere VPC, subnets, key pair,
perfil IAM ni parametros adicionales. `CaseId` solo se interpola en etiquetas,
nunca en comandos shell. Para repetir un experimento se debe registrar el AMI ID
resuelto (`ResolvedValue` del parametro del stack): `latest` puede cambiar.

Cada plantilla retorna `ApplicationUrl` (sin barra final) y `VpcId`.
A tambien retorna `InstanceId`; B/C retornan `LoadBalancerFullName`
(dimension `LoadBalancer` de `AWS/ApplicationELB`, no el ARN) y
`AutoScalingGroupName` (nombre fisico, no ID logico).

## Arranque y demo

Las tres arquitecturas ejecutan la misma demo: nginx en TCP 80 hace proxy a un
servidor Python de biblioteca estandar en `127.0.0.1:8000`, bajo systemd como
`nobody`. Ambos servicios se habilitan al arranque y Python se reinicia si falla.

- `GET /`: JSON con `service`, `status`, `host`; ejecuta PBKDF2-HMAC-SHA256 con
  25 000 iteraciones fijas para que la carga pueda ejercitar CPU en B/C.
- `GET /health`: JSON HTTP 200, sin trabajo CPU artificial, comprobando nginx y
  Python. Se usa tambien como health check del ALB.
- Otras rutas: HTTP 404. No se despliega aqui la API de negocio de SECI-TI.

UserData usa `set -Eeuo pipefail`, tres intentos acotados de `dnf install`
(`nginx`, `python3`, `aws-cfn-bootstrap`) y un limite global de 540 segundos para
instalar, configurar y comprobar ambos endpoints. Una trampa `EXIT` conserva el
codigo de salida y envia `cfn-signal` al recurso EC2/ASG correcto; tiene tres
intentos de hasta 20 segundos. Un fallo genera una senal de fallo si el helper y
la red estan disponibles. Si ni siquiera puede instalarse el helper o enviarse
la senal, `CreationPolicy` falla por timeout de 12 minutos. C exige senales de sus
dos instancias iniciales y B de su instancia inicial.

`CREATE_COMPLETE` espera al bootstrap local, no demuestra que una prueba HTTP
desde el cliente haya pasado. La propagacion DNS y el registro/health check del
ALB pueden requerir unos segundos adicionales. Verificar `ApplicationUrl` y
`ApplicationUrl/health` antes de iniciar k6. El objetivo RQ-12 de 15 minutos debe
medirse, incluyendo provisionamiento y bootstrap.

Los logs quedan en `/var/log/seci-ti-bootstrap.log`, `/var/log/cloud-init-output.log`,
`/var/log/nginx/` y el journal de `seci-ti-demo`. No se configura envio de logs a
CloudWatch porque requeriria permisos en la instancia. El bootstrap tambien
escribe en la consola EC2 para diagnosticar fallos sin SSH.

## Red y seguridad

Cada stack crea su propia VPC `10.42.0.0/16`, Internet Gateway, tabla de rutas y
subnets publicas `/24`; pueden coexistir porque no se interconectan. Las
instancias tienen IPv4 publica para descargar paquetes y enviar senales HTTPS,
sin NAT Gateway ni endpoints privados. Las dependencias explicitas aseguran la
ruta y las asociaciones de subnets antes del arranque.

Se permite **HTTP 80 desde `0.0.0.0/0` deliberadamente para el laboratorio**,
sin TLS ni autenticacion. Usar exclusivamente datos ficticios. A expone EC2;
B/C exponen el ALB y el SG de la app acepta TCP 80 solamente desde el SG del
ALB, incluso si EC2 tiene IP publica. El ALB solo puede salir por TCP 80 hacia
la VPC; las apps salen por TCP 80/443 para repositorios y CloudFormation.
El puerto Python 8000 solo escucha en loopback. No hay SSH, RDP, key pair,
`IamInstanceProfile` ni recursos `AWS::IAM::*`.

IMDSv2 es obligatorio, con hop limit 1. El disco raiz gp3 de 8 GiB se cifra con
la clave EBS predeterminada de AWS y se elimina con la instancia, sin crear
claves KMS propias. EC2 tiene detailed monitoring (CPU cada minuto). CloudFormation
aplica automaticamente sus etiquetas reservadas `aws:cloudformation:*` segun
soporte de cada recurso. `CaseId` se aplica explicitamente a los recursos que
admiten etiquetas; las instancias y discos tambien reciben `Project`,
`Architecture` y `StackName`. El ASG propaga las etiquetas a nuevas instancias;
el launch template etiqueta los volumenes nuevos.

## Escalado y limites de Learner Lab

B/C usan target tracking de `ASGAverageCPUUtilization` al 50 %, warmup de
120 segundos y scale-in habilitado, dentro de sus limites. Se publican metricas
ASG cada minuto (`GroupDesiredCapacity`, `GroupInServiceInstances`, pendientes,
terminando y total). El ASG usa health checks ELB, gracia de 600 segundos para
no reciclar instancias durante el bootstrap, y deregistration delay de
30 segundos. Las actualizaciones del launch template usan rolling update con
senales al 100 % y pausa maxima de 12 minutos por lote. No se debe cambiar el
bootstrap de una EC2 A existente esperando una reejecucion automatica de UserData;
para experimentos comparables usar stacks nuevos.

La cuenta necesita acceso permitido a EC2, VPC, ELB, Auto Scaling,
CloudFormation y al parametro SSM publico. B/C requieren una region con al menos
dos AZ disponibles y los service-linked roles de Auto Scaling/ELB ya habilitados
en el laboratorio: las plantillas no crean roles, pero los servicios dependen
de ellos. Un laboratorio que bloquee esos servicios/roles requiere intervencion
de su administrador; adjuntar un perfil IAM a la app no lo resuelve.

No se crean alarmas de target tracking manualmente: Auto Scaling las gestiona.
La frecuencia de metricas y warmup no garantizan un tiempo de scale-out de cinco
minutos (RQ-03). La demo, la carga, los creditos CPU t2/t3 y la capacidad de la
cuenta deben calibrarse experimentalmente. A no tiene metricas ALB de latencia,
errores o hosts saludables: la medicion HTTP corresponde a k6. Los costos incluyen
EC2, EBS, IPv4 publicas, monitoring, ALB/LCU y transferencia. Registrar region,
duracion y capacidad para estimar RQ-09; estas plantillas no fijan precios ni
garantizan una cuota gratuita. Eliminar los stacks tras las pruebas para liberar
recursos y detener esos cargos.

## Validacion local

Con PyYAML y las dependencias de desarrollo del backend instaladas, desde la raiz:

```powershell
python -m pytest backend/tests/test_infrastructure_templates.py
```

La suite comprueba contrato YAML, topologia, seguridad, outputs, senales,
observabilidad, etiquetas y coherencia de la demo sin credenciales ni llamadas
AWS. Opcionalmente, con `cfn-lint` instalado:

```powershell
cfn-lint infrastructure/architecture-a/template.yaml infrastructure/architecture-b/template.yaml infrastructure/architecture-c/template.yaml
```

## Referencias

- [Subnets ALB: dos AZ y al menos /27](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html#subnets-load-balancer).
- [cfn-signal y autenticacion por pertenencia al stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/cfn-signal.html).
- [CreationPolicy y numero de senales](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-creationpolicy.html).
- [Helpers de CloudFormation y permisos](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/cfn-helper-scripts-reference.html).
- [Service-linked roles de Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-service-linked-role.html).
