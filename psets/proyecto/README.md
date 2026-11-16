# OralSolutions — Predicción de Abandono de Tratamientos Odontológicos

Proyecto de ciencia de datos que prepara y modela los registros clínicos, operativos y financieros de la clínica odontológica **OralSolutions** con el objetivo de predecir la probabilidad de que un paciente activo abandone su tratamiento en los próximos 60 días tras cada consulta atendida. Con esta predicción, el equipo administrativo y clínico prioriza recordatorios personalizados y reprogramaciones preventivas antes de que se pierda la continuidad del tratamiento, reemplazando la gestión puramente reactiva actual.

**Métrica de éxito:** Incrementar en **10 puntos porcentuales** la tasa de continuidad de tratamientos a 60 días frente al seguimiento reactivo habitual (línea base), activando alertas preventivas cuando la probabilidad predicha de abandono sea $\ge 60\%$ (umbral justificado porque el costo operativo de un contacto preventivo es significativamente menor al costo clínico y financiero de perder un tratamiento recurrente).

## Datos

| Fuente | Qué contiene | Cómo se obtiene | Dónde queda |
|---|---|---|---|
| Dataset clínico-operativo OralSolutions (11 archivos CSV) | 38,603 registros distribuidos en: `patients.csv`, `dentists.csv`, `insurers.csv`, `procedures.csv`, `treatment_plans.csv`, `treatment_sessions.csv`, `treatment_lines.csv`, `appointments.csv`, `missed_appointments.csv`, `patient_followups.csv` e `invoices.csv` (citas, planes de tratamiento, sesiones, facturación, aseguradoras y seguimientos). | Archivos fuente del proyecto colocados localmente en `data/raw/` y verificados mediante el script de ingesta contenedorizado antes de su carga hacia el warehouse. | `data/raw/*.csv` |

Los datos no están en el repositorio (ignorados por `.gitignore`). Para obtener y verificar los archivos desde cero (desde `psets/proyecto/`):

- **Alternativa 1 — Descarga y verificación automática (recomendada):**
  Ejecutar `ingesta/ingestar.py`, el cual comprueba si los 11 CSV ya existen localmente y, de no estar presentes, los descarga automáticamente desde Google Drive y verifica sus **38,603 registros**:

```powershell
  # En local (con el entorno virtual activado)
  python ingesta/ingestar.py

  # O mediante contenedor Docker aislado
  docker build -t oralsolutions-ingesta .
  docker run --rm -v "${PWD}\data\raw:/app/data/raw" oralsolutions-ingesta
```
- **Alternativa 2 — Descarga manual de respaldo:** Si la descarga automática falla por restricciones de red, descargar manualmente los 11 archivos CSV desde la [carpeta de Google Drive](https://drive.google.com/drive/folders/1bDd9OOZ1SPTLjnGQld5IIn-x4Gp8KQIh?usp=drive_link), pegarlos dentro de `psets/proyecto/data/raw/` y volver a ejecutar `python ingesta/ingestar.py` para confirmar que todos los archivos y conteos estén íntegros.

## Cómo correr el pipeline de datos

Implementa un pipeline ELT reproducible que procesa los **11 archivos CSV** mediante **Kestra → Snowflake Raw → dbt (Bronze, Silver y Gold) → Apache Spark → Snowflake OBT**, además de incluir una cadena local de calidad y warehouse en **DuckDB** (`calidad/` y `warehouse/construir_warehouse.py`).

### 1. Estructura del proyecto

```text
psets/proyecto/
├── Dockerfile                   # Imagen base de ingesta y validación
├── Dockerfile.dbt               # Imagen de dbt Core con adaptador Snowflake
├── requirements.txt             # Dependencias Python del proyecto
├── .env.example                 # Plantilla de variables de entorno
├── data/
│   ├── raw/                     # 11 CSV de origen (ignorados por Git)
│   └── processed/               # 11 CSV limpios generados por calidad/limpiar.py
├── ingesta/
│   └── ingestar.py              # Descarga desde Drive y verificación de los 11 CSV
├── calidad/
│   ├── diagnostico_proyecto.ipynb # Análisis de calidad por tabla y dimensión
│   └── limpiar.py               # Script reproducible de limpieza
├── warehouse/
│   ├── construir_warehouse.py   # Carga y verificación de filas en DuckDB
│   └── dbt/                     # Modelos y pruebas Bronze, Silver y Gold
├── procesamiento/
│   └── job_spark.py             # Construcción y validación de la OBT con Spark
├── orquestacion/
│   ├── ingest_raw_oralsolutions.yml
│   ├── test_dbt_docker.yml
│   ├── test_spark_docker.yml
│   ├── backfill_appointments.yml
│   └── flow_proyecto.yml        # Flujo maestro (id: flow_proyecto)
├── infra/
│   ├── docker-compose.yml       # PostgreSQL, Kestra, Spark y dbt
│   ├── config/dbt/              # Plantilla y perfil privado de dbt
│   └── sql/                     # Inicialización de Snowflake
└── docs/                        # Canvas, propuesta, presentación y memo técnico
```

### 2. Requisitos previos y entorno Python
- **Docker Desktop** con Docker Compose y contenedores Linux. Los comandos siguientes están escritos para **PowerShell en Windows**.
- **Python 3.11+** con un entorno virtual dedicado donde se instalen las librerías de requirements.txt (numpy, pandas, python-dotenv, requests, gdown, duckdb, pytest):

```PowerShell
# Crear y activar entorno virtual en PowerShell (desde psets/proyecto/)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt<>
```

(En Linux / GitHub Codespaces: 
```
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt).
```

- **Cuenta de Snowflake** con permisos `ACCOUNTADMIN` y un método de autenticación compatible con conexiones **usuario/contraseña**.
- Conexión a Internet para descargar los datos desde Google Drive, conectar con Snowflake y descargar las imágenes/dependencias de Docker y Spark.
- Los **11 archivos CSV** descargados y verificados en `data/raw/` (mediante `python ingesta/ingestar.py`).

> Salvo los scripts SQL (que se ejecutan en **Snowsight**), todos los comandos se ejecutan desde **`psets/proyecto/`**.

#### Configuración requerida en Snowflake
La implementación actual utiliza estos nombres en los scripts SQL y en los flujos YAML; **cambiar las variables `SNOWFLAKE_*` de `.env` no cambia automáticamente los valores escritos en los flujos de Kestra**.

|**Recurso**|**Nombre o requisito utilizado**|
|---|---|
|Base de datos|`ORALSOLUTIONS_DW`|
|Warehouse|`COMPUTE_WH`|
|Rol de los flujos JDBC de Kestra|`ACCOUNTADMIN`|
|Esquemas|`RAW`, `BRONZE`, `SILVER`, `GOLD`, `OBT`|
|Autenticación actual|Usuario y contraseña admitidos por la cuenta|

En una cuenta nueva, utilizar estos nombres y los permisos correspondientes. Si se desea utilizar otro rol, warehouse o nombre de base de datos, habrá que modificar **de manera coherente los YAML, scripts SQL, perfil dbt y configuración de Spark**. La inicialización SQL crea el warehouse, la base, los esquemas, las tablas Raw, el formato CSV y el stage, pero **no aprovisiona el usuario**.

### 3. Obtener los datos y configurar credenciales privadas

1. **Descargar y verificar los 11 archivos CSV en `data/raw/`:**

```PowerShell
python ingesta/ingestar.py
```

_(Confirma que los 11 archivos y sus **38,603 registros** estén disponibles en `data/raw/`)._

2. **Crear los archivos locales de configuración a partir de las plantillas públicas (ignorados por `.gitignore`):**

```PowerShell
Copy-Item .env.example .env
Copy-Item infra/config/dbt/profiles.example.yml infra/config/dbt/profiles.yml
```

En Linux / GitHub Codespaces:

```bash
cp .env.example .env
cp infra/config/dbt/profiles.example.yml infra/config/dbt/profiles.yml
```

- **En `.env`:** completar `KESTRA_DB_PASSWORD`, `KESTRA_ADMIN_EMAIL`, `KESTRA_ADMIN_PASSWORD`, `ENV_SNOWFLAKE_URL`, `ENV_SNOWFLAKE_USER`, `SF_ACCOUNT`, `SF_USER`, `SF_WAREHOUSE=COMPUTE_WH`, `SF_DATABASE=ORALSOLUTIONS_DW`, `SF_GOLD_SCHEMA=GOLD`, `SF_OBT_SCHEMA=OBT`, `SF_ROLE=ACCOUNTADMIN`, `SECRET_SNOWFLAKE_PASSWORD` (contraseña en Base64 UTF-8) y `ENV_KESTRA_HOST_PROJECT_PATH` (ruta absoluta de `psets/proyecto/` visible para Docker, guardando `.env` en UTF-8 sin BOM con finales de línea `LF`).

```PowerShell
# Generar SECRET_SNOWFLAKE_PASSWORD en Base64:
python -c "import base64,getpass; print(base64.b64encode(getpass.getpass('Contraseña Snowflake: ').encode('utf-8')).decode('ascii'))"
```

- **En `infra/config/dbt/profiles.yml`:** completar `account`, `user`, `password` (texto plano, sin Base64), `role: ACCOUNTADMIN` y `warehouse: COMPUTE_WH` manteniendo el perfil `oralsolutions`, target `dev` y base `ORALSOLUTIONS_DW`.

### 4. Cadena local de calidad y warehouse (DuckDB)
1. **Diagnóstico y limpieza de datos (`data/raw/*.csv` → `data/processed/*.csv`):**

```PowerShell
python calidad/limpiar.py
```

(Aplica las reglas documentadas en calidad/diagnostico_proyecto.ipynb y guarda los 11 CSV limpios en data/processed/).

2. **Carga al warehouse local DuckDB y verificación de filas:**

```PowerShell
python warehouse/construir_warehouse.py
```

(Crea `warehouse/oralsolutions.duckdb` verificando que las **38,603 filas** cargadas coincidan exactamente con los CSV limpios).
*(Nota: En entornos limpios como un Codespace nuevo, la primera ejecución del paso de Spark tarda ~9–10 minutos mientras descarga los conectores Maven/Ivy de Snowflake; en ejecuciones posteriores reutiliza el volumen caché `spark_ivy`).*

### 5. Pipeline End-to-End en Docker + Snowflake (Kestra → dbt → Spark)
1. **Inicializar Snowflake (en Snowsight):** ejecutar en orden:
    - `infra/sql/01_setup_snowflake.sql`: crea el warehouse `COMPUTE_WH`, la base `ORALSOLUTIONS_DW` y los esquemas `RAW`, `BRONZE`, `SILVER`, `GOLD` y `OBT`.
    - `infra/sql/02_create_raw_tables.sql`: crea las 11 tablas en `RAW`, el formato `CSV_RAW_FORMAT` y el stage `RAW_CSV_STAGE`.

2. **Construir imagen de dbt y levantar infraestructura:**

```PowerShell
docker build -f Dockerfile.dbt -t pset_2-dbt:latest .
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 config --quiet
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 up -d postgres kestra spark dbt
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 exec dbt dbt debug
```

3. **Importar flujos en Kestra (`http://localhost:8080`):** crear y guardar los YAML de `orquestacion/` en el namespace `oralsolutions` en este orden:
    
    1. `orquestacion/ingest_raw_oralsolutions.yml`
    2. `orquestacion/test_dbt_docker.yml`
    3. `orquestacion/test_spark_docker.yml`
    4. `orquestacion/backfill_appointments.yml` _(opcional para recuperación histórica parametrizada)_
    5. `orquestacion/flow_proyecto.yml` (**maestro**, `id: flow_proyecto`)

4. **Ejecutar el pipeline maestro:** abrir `oralsolutions.flow_proyecto` en Kestra y seleccionar **Execute**. Ejecuta secuencialmente la ingesta idempotente a `RAW` (con reintentos exponenciales `maxAttempts: 3`), las transformaciones `dbt run` y `dbt test` (`BRONZE`, `SILVER`, `GOLD`), y la construcción de `OBT.OBT_RIESGO_ABANDONO` mediante `procesamiento/job_spark.py`.

### 6. Verificar resultados y operaciones opcionales
Resultados esperados en Snowflake: **11** tablas cargadas en `RAW` (**38,603** registros), **28** modelos dbt, **177** pruebas aprobadas, **6,794** eventos en `GOLD.FACT_SESIONES_TRATAMIENTO` y **3,435** puntos candidatos únicos en `OBT.OBT_RIESGO_ABANDONO`.

```PowerShell
# Ejecución manual de dbt (desde psets/proyecto/)
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 exec dbt dbt run
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 exec dbt dbt test

# Ejecución manual de Spark (desde psets/proyecto/)
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 exec spark /opt/spark/bin/spark-submit --master 'local[*]' --packages 'net.snowflake:spark-snowflake_2.12:3.2.3-spark_3.5,net.snowflake:snowflake-jdbc:4.0.2' /opt/spark/work-dir/job_spark.py

# Detener servicios sin borrar volúmenes
docker compose -f infra/docker-compose.yml --env-file .env --project-name pset_2 down
```

### Decisión de procesamiento: Batch vs. Streaming
Este proyecto utiliza procesamiento por lotes (batch) diario (0 2 * * *, America/Guayaquil) y no requiere streaming, debido a que la decisión de negocio que habilita (priorizar llamadas, mensajes de seguimiento y reprogramaciones preventivas para pacientes con riesgo de abandonar su tratamiento en los próximos 60 días) no pierde valor con datos de horas de antigüedad. Durante la jornada diurna y vespertina la clínica registra citas y sesiones de forma progresiva, por lo que consolidar los datos en la madrugada permite que el equipo administrativo disponga cada mañana de las alertas actualizadas sin interferir con la operación clínica ni asumir la complejidad operativa de una arquitectura continua de baja latencia.

## Cómo entrenar y evaluar el modelo

[Qué notebook corre cada etapa del modelado, en qué orden, y qué necesita levantado (MLflow). Se completa con el PSet 3.]

## Modelo final

[El modelo elegido, su `run_id` en MLflow y la métrica que lo sostiene. El razonamiento completo está en `docs/decision_modelo.md`. Se completa con el PSet 3.]

## Cómo correr el servicio

[Cómo se construye y se levanta el contenedor de `servicio/`, qué versión del modelo carga desde el registro, y un ejemplo de petición con su respuesta. Se completa con el PSet 4.]