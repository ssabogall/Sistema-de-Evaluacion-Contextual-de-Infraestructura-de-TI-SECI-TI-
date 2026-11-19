# Arquitectura C: resiliente en dos AZ

[`template.yaml`](template.yaml) crea una VPC, dos subnets publicas `/24` en
AZ distintas, ALB en ambas y un ASG distribuido entre las dos subnets.
Capacidad inicial y minima: 2; maxima: 4. Auto Scaling balancea las instancias
entre AZ segun disponibilidad de capacidad; la distribucion real debe
comprobarse antes de simular fallos de zona. No se usa Placement fijado a una AZ.

La demo nginx/Python, el target tracking al 50 % de CPU, warmup de
120 segundos, detailed monitoring y metricas ASG de un minuto son los mismos
que B. `/health` se comprueba cada 15 segundos; el ASG usa health checks ELB
con gracia inicial de 600 segundos y cross-zone habilitado. La minima de dos
instancias preserva redundancia tras scale-in, sujeta a fallos y reemplazos.

C permite evaluar RQ-05, RQ-06 y RQ-07: al perder una instancia/AZ, los
targets saludables de la otra pueden seguir atendiendo. Puede haber errores
mientras el ALB detecta la perdida y la capacidad superviviente puede
saturarse. Los porcentajes de exito y tiempos de recuperacion son objetivos
experimentales, no garantias del template. Registrar distribucion por AZ,
`HealthyHostCount` y capacidad antes, durante y despues del fallo.

El backend envia solo `InstanceType` (`t3.micro` por defecto; admite
`t2.micro`) y `CaseId`. `LatestAmiId` usa el parametro SSM publico de AL2023
x86_64. Outputs: `ApplicationUrl`, `VpcId`, `LoadBalancerFullName` y
`AutoScalingGroupName`, listos para consultas de metricas posteriores.

El ASG exige senales de **las dos instancias iniciales** antes de
`CREATE_COMPLETE`. Cada bootstrap instala y comprueba la demo con un limite
de nueve minutos; `CreationPolicy` espera 12 minutos. Los rolling updates
mantienen al menos dos instancias en servicio y esperan senales por lote;
esto no certifica la distribucion por AZ durante la actualizacion.

HTTP 80 publico se permite solo en el ALB para laboratorio. El SG de las apps
acepta TCP 80 exclusivamente desde el SG del ALB; sus IPv4 publicas sirven
para paquetes/senales sin NAT. No hay SSH, perfil IAM ni recursos IAM.
IMDSv2 obligatorio y discos gp3 cifrados, con etiquetas propagadas al escalar.

Requiere dos AZ y servicios/service-linked roles permitidos por Learner Lab.
Costos base: ALB/LCU, de dos a cuatro EC2 con sus discos de 8 GiB e IPv4,
IPv4 del ALB, detailed monitoring y transferencia. Leer el
[contrato, validacion, bootstrap y limites comunes](../README.md).
