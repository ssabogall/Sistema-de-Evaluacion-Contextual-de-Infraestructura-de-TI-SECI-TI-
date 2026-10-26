# Arquitectura B: escalable con computo en una AZ

[`template.yaml`](template.yaml) crea una VPC y dos subnets publicas `/24` en
AZ distintas. El ALB necesita ambas AZ; el ASG usa **solo la primera subnet**.
Esto conserva la diferencia experimental frente a C: B escala, pero el
computo depende de una sola AZ. Cross-zone esta habilitado para que ambos
nodos del ALB alcancen los targets de esa AZ.

El ASG inicia con una instancia, minimo 1 y maximo 3. Usa target tracking al
50 % de CPU media, warmup de 120 segundos, detailed monitoring y metricas ASG
de un minuto. El target group comprueba `GET /health` cada 15 segundos;
el ASG reemplaza targets fallidos con health check ELB y gracia inicial de
600 segundos. La demo nginx/Python ejecuta el mismo trabajo CPU fijo que A/C.

**Con la capacidad inicial de una instancia, perderla interrumpe el servicio
hasta su reemplazo.** RQ-05 (99 % de exito durante caida) solo puede evaluarse
con redundancia ya presente, por ejemplo tras escalar a dos instancias.
El escalado dentro de una AZ tampoco protege ante perdida de esa AZ. Los
objetivos RQ-02, RQ-03 y RQ-07 necesitan medir carga, alarmas y recuperacion;
no se garantizan por los limites configurados.

El backend envia solo `InstanceType` (`t3.micro` por defecto, tambien
`t2.micro`) y `CaseId`; `LatestAmiId` tiene el default SSM de AL2023 x86_64.
Outputs: `ApplicationUrl`, `VpcId`, `LoadBalancerFullName` y
`AutoScalingGroupName`. Los dos ultimos identifican las dimensiones para
`AWS/ApplicationELB` y `AWS/AutoScaling`/`AWS/EC2` respectivamente.

HTTP 80 publico llega solo al ALB. Las EC2 tienen IP publica para bootstrap,
pero su SG acepta HTTP exclusivamente desde el SG del ALB. No hay SSH,
perfil IAM ni NAT. IMDSv2 obligatorio y volumenes gp3 cifrados. El ASG espera
una senal de bootstrap exitoso, con timeout de 12 minutos y limite de nueve
minutos para instalar y verificar la demo. Los rolling updates tambien
esperan senales y mantienen al menos una instancia en servicio.

La cuenta necesita las dos AZ, los servicios y los service-linked roles
permitidos por Learner Lab. No se crean recursos IAM en la plantilla.
Costos base: ALB/LCU, de una a tres EC2 con sus discos de 8 GiB e IPv4,
IPv4 del ALB, detailed monitoring y transferencia. Leer el
[contrato, validacion, bootstrap y limites comunes](../README.md).
