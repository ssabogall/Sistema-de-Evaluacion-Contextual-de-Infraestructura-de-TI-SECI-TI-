# PB-03: conexion y despliegue AWS

## Alcance

Esta fase conecta el caso confirmado y la recomendacion de PB-02 con AWS.
Incluye verificacion de identidad mediante STS y crear, consultar y eliminar
un stack de CloudFormation por caso. La arquitectura se obtiene del caso
guardado: el navegador no envia plantillas, credenciales ni una arquitectura
alternativa. No se llama a un modelo de IA para operar AWS.

El catalogo contiene tres plantillas versionadas:

| Arquitectura | Computo | Balanceo |
| --- | --- | --- |
| A | Una EC2 en una zona | Acceso HTTP directo |
| B | Auto Scaling en una zona | ALB en dos zonas |
| C | Auto Scaling en dos zonas | ALB en dos zonas |

Las instancias ejecutan una aplicacion HTTP de laboratorio. Esto despliega la
infraestructura evaluada, no aloja el frontend y backend de SECI-TI en AWS.
Las plantillas no crean roles IAM, llaves SSH ni NAT Gateways. HTTP publico es
exclusivamente para el experimento; no se debe enviar informacion sensible.
Todavia no hay automatizacion de k6, recoleccion CloudWatch ni migracion de SQLite.

## Configurar el equipo

Instala las dependencias del README y crea `.env` en la raiz si no existe:

```powershell
Copy-Item .env.example .env
```

Cada integrante configura sus propias credenciales locales. No sobrescribas un
`.env` existente ni publiques claves o archivos de credenciales en GitHub.

### AWS Academy Learner Lab

1. Inicia la sesion del laboratorio (Start Lab).
2. En AWS Details, consulta las credenciales de AWS CLI.
3. En tu `.env`, completa los tres valores de esa misma sesion:

```dotenv
AWS_ENABLED=true
AWS_ALLOW_DEPLOYMENTS=false
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=valor_de_la_sesion
AWS_SECRET_ACCESS_KEY=valor_de_la_sesion
AWS_SESSION_TOKEN=valor_de_la_sesion
AWS_EXPECTED_ACCOUNT_ID=123456789012
```

Reemplaza el ID por el de tu propia cuenta de laboratorio. El token es obligatorio
con credenciales temporales. Si la sesion expira, renueva los tres valores y
reinicia el backend. Las credenciales de OpenAI/Gemini y AWS son independientes.

### Perfil AWS o rol de la maquina

Tambien se admite la cadena normal de credenciales de Boto3: perfiles compartidos,
SSO previamente autenticado y roles de ejecucion. Por ejemplo, para un perfil
ya configurado con AWS CLI, quita las tres claves explicitas de `.env` y usa:

```dotenv
AWS_ENABLED=true
AWS_PROFILE=seci-ti
AWS_REGION=us-east-1
AWS_EXPECTED_ACCOUNT_ID=123456789012
```

No combines `AWS_PROFILE` con claves explicitas en `.env` o en el entorno del
proceso. Los archivos compartidos normales estan en el directorio `.aws` del
usuario. Para roles de ejecucion no definas ni perfil ni claves.

## Verificar y desplegar

1. Inicia backend y frontend desde el README.
2. Verifica `GET http://localhost:8000/api/aws/connection`, o abre un caso guardado.
   Debe indicar `connected`, tu cuenta y tu region. Esta comprobacion solo valida
   identidad; los permisos de CloudFormation se comprueban al operar.
3. Revisa cuenta, region y presupuesto. Para permitir cambios, configura
   `AWS_ALLOW_DEPLOYMENTS=true` y reinicia el backend.
4. Abre el caso y confirma la creacion desde el panel AWS. Se despliega unicamente
   la arquitectura que recomendo el motor. Mientras se crea, el panel consulta
   su estado periodicamente.
5. Cuando CloudFormation termine, abre `ApplicationUrl`. Los eventos muestran
   problemas de arranque o recursos sin permisos; `CREATE_IN_PROGRESS` no equivale
   a una aplicacion disponible.
6. Al terminar las pruebas, confirma la eliminacion y espera a `NOT_DEPLOYED`
   o `DELETE_COMPLETE`. Cerrar el navegador no elimina los recursos.

Las instancias, el ALB, almacenamiento y trafico pueden generar cargos contra
el presupuesto del laboratorio o la cuenta conectada. No hay una estimacion
automatica de costos. Antes de reutilizar una cuenta, comprueba que no queden
stacks activos de experimentos anteriores.

## Variables

| Variable | Valor predeterminado | Uso |
| --- | --- | --- |
| `AWS_ENABLED` | `false` | Habilita llamadas AWS; apagado no hace conexiones |
| `AWS_ALLOW_DEPLOYMENTS` | `false` | Permite crear y eliminar stacks |
| `AWS_REGION` | `us-east-1` | Region del experimento |
| `AWS_STACK_PREFIX` | `seci-ti` | Prefijo de nombres de stack |
| `AWS_INSTANCE_TYPE` | `t3.micro` | `t3.micro` o `t2.micro` segun disponibilidad del lab |
| `AWS_EXPECTED_ACCOUNT_ID` | Sin valor | Rechaza una identidad de otra cuenta |
| `AWS_PROFILE` | Sin valor | Perfil SDK/CLI existente, alternativa a claves |
| `AWS_ACCESS_KEY_ID` | Sin valor | Identificador de credencial |
| `AWS_SECRET_ACCESS_KEY` | Sin valor | Secreto de credencial |
| `AWS_SESSION_TOKEN` | Sin valor | Token para credenciales temporales |

No cambies cuenta, region ni prefijo mientras existan stacks activos: la consulta
busca el nombre deterministico `<AWS_STACK_PREFIX>-<case_id>` en esa cuenta y
region. CloudFormation es la fuente de verdad del despliegue; SQLite conserva
el caso y la recomendacion, no una copia potencialmente desactualizada del stack.
Conserva la base de datos del experimento para mantener la relacion con sus casos.
Si se pierde esa base, los stacks permanecen visibles y eliminables desde AWS.

## Permisos

Se necesita acceso a STS y a estas operaciones de CloudFormation:
`DescribeStacks`, `DescribeStackEvents`, `ValidateTemplate`, `CreateStack`
y `DeleteStack`. El rol usado por CloudFormation tambien debe permitir los
recursos de las plantillas: VPC, subnets, rutas, internet gateway, security groups,
EC2/launch templates, Auto Scaling, ELBv2, alarmas CloudWatch y lectura del parametro
SSM publico de la AMI de Amazon Linux. No se exige una politica AdministratorAccess.

Las restricciones del Learner Lab pueden bloquear operaciones o tipos de instancia.
El proyecto informa el fallo, pero no cambia los permisos ni intenta evadirlos.

## API

| Metodo | Ruta | Resultado |
| --- | --- | --- |
| GET | `/api/aws/connection` | Identidad, region y cambios habilitados |
| GET | `/api/cases/{id}/deployment` | Estado, outputs y 15 eventos recientes |
| POST | `/api/cases/{id}/deployment` | Acepta `{"confirm_costs": true}`, devuelve 202 |
| DELETE | `/api/cases/{id}/deployment` | Inicia eliminacion y devuelve 202 |

Una solicitud aceptada no significa que la operacion AWS haya terminado. Consulta
el estado hasta un estado final. Un POST repetido mientras se crea o cuando ya
esta creado devuelve el stack existente; no crea otro. Un stack fallido debe
eliminarse antes de volver a crear. La eliminacion usa el ARN del stack verificado.

Cada stack lleva etiquetas `Application=SECI-TI`, `CaseId` y `Architecture`.
Una coincidencia de nombre sin esas etiquetas devuelve 409 y no se modifica.
Los errores de configuracion devuelven 503, los de permisos 403, los conflictos
409 y los fallos del proveedor 502. Un caso inexistente devuelve 404 sin llamar AWS.

La API conserva el alcance local del prototipo, sin autenticacion multiusuario.
No expongas estos endpoints de control a Internet sin incorporar autenticacion
y autorizacion. CORS por si solo no restringe clientes fuera del navegador.

## Verificacion

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\cfn-lint.exe infrastructure/architecture-a/template.yaml infrastructure/architecture-b/template.yaml infrastructure/architecture-c/template.yaml
npm test --prefix frontend
npm run build --prefix frontend
```

Los tests AWS usan clientes con credenciales ficticias y `botocore.stub.Stubber`.
Verifican cuenta, permisos, estados, propiedad del stack, idempotencia y creacion
de la plantilla correspondiente. No se crean recursos ni se usan tokens de IA.
La prueba real depende de una sesion AWS valida y debe registrar el ID del stack,
el resultado de `/health` de la aplicacion y la eliminacion completa.

Referencias oficiales: [credenciales Boto3](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html),
[CreateStack](https://docs.aws.amazon.com/boto3/latest/reference/services/cloudformation/client/create_stack.html),
[GetCallerIdentity](https://docs.aws.amazon.com/boto3/latest/reference/services/sts/client/get_caller_identity.html).
