# Arquitectura A: basica

[`template.yaml`](template.yaml) crea una VPC, una subnet publica `/24` en la
primera AZ disponible, Internet Gateway y una unica EC2 AL2023 con nginx/Python.
No hay balanceador, Auto Scaling ni recuperacion automatica de la aplicacion
ante perdida de la instancia o de la AZ.

El backend envia solo `InstanceType` (`t3.micro` predeterminado; tambien admite
`t2.micro`) y `CaseId`. `LatestAmiId` se resuelve automaticamente desde el
parametro publico SSM de AL2023 x86_64. Outputs: `ApplicationUrl`, `VpcId`,
`InstanceId`; la URL usa la IPv4 publica de EC2 y puede cambiar si se detiene y
arranca la instancia. Para la demo y todos los parametros ver el
[contrato comun](../README.md).

HTTP 80 esta abierto a Internet para pruebas de laboratorio. Python escucha
solo en loopback; no hay SSH, key pair ni perfil IAM. IMDSv2 es obligatorio,
el disco gp3 esta cifrado y EC2 tiene detailed monitoring de un minuto.

La EC2 exige una senal `cfn-signal` tras comprobar `GET /health` y `GET /`.
El bootstrap tiene un limite de nueve minutos y `CreationPolicy` espera hasta
12 minutos: un fallo o falta de senal impide `CREATE_COMPLETE`. La red publica
se crea antes de lanzar la instancia. Para repetir pruebas, usar un stack
nuevo; UserData no es un mecanismo de actualizacion de la aplicacion.

Permite comparar RQ-01, RQ-04 y RQ-08, ademas de seguridad, observabilidad y
reproducibilidad (RQ-09 a RQ-12). La perdida de la unica EC2 interrumpe el
servicio. CPU se obtiene de `AWS/EC2` con `InstanceId`; latencia y errores HTTP
se miden desde k6, dado que A no tiene ALB. Los objetivos requieren validacion
experimental y registro de costos; no quedan certificados por la plantilla.

Costos base: una EC2, un disco EBS de 8 GiB, una IPv4 publica y detailed
monitoring, mas transferencia. Consultar [validacion y limites](../README.md)
antes de desplegar. Este cambio no ejecuta operaciones AWS.
