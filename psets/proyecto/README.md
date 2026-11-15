# OralSolutions — Predicción de Abandono de Tratamientos Odontológicos

Proyecto de ciencia de datos que prepara y modela los registros clínicos, operativos y financieros de la clínica odontológica **OralSolutions** con el objetivo de predecir la probabilidad de que un paciente activo abandone su tratamiento en los próximos 60 días tras cada consulta atendida. Con esta predicción, el equipo administrativo y clínico prioriza recordatorios personalizados y reprogramaciones preventivas antes de que se pierda la continuidad del tratamiento, reemplazando la gestión puramente reactiva actual.

**Métrica de éxito:** Incrementar en **10 puntos porcentuales** la tasa de continuidad de tratamientos a 60 días frente al seguimiento reactivo habitual (línea base), activando alertas preventivas cuando la probabilidad predicha de abandono sea $\ge 60\%$ (umbral justificado porque el costo operativo de un contacto preventivo es significativamente menor al costo clínico y financiero de perder un tratamiento recurrente).

## Datos

| Fuente | Qué contiene | Cómo se obtiene | Dónde queda |
|---|---|---|---|
| Dataset clínico-operativo OralSolutions (11 archivos CSV) | 38,603 registros distribuidos en: `patients.csv`, `dentists.csv`, `insurers.csv`, `procedures.csv`, `treatment_plans.csv`, `treatment_sessions.csv`, `treatment_lines.csv`, `appointments.csv`, `missed_appointments.csv`, `patient_followups.csv` e `invoices.csv` (citas, planes de tratamiento, sesiones, facturación, aseguradoras y seguimientos). | Archivos fuente del proyecto colocados localmente en `data/raw/` y verificados mediante el script de ingesta contenedorizado antes de su carga hacia el warehouse. | `data/raw/*.csv` |

Los datos no están en el repositorio (ignorados por `.gitignore`). Para verificar y preparar los archivos desde cero en local o mediante Docker:

```powershell
# Opción 1: Verificación directa en local (desde psets/proyecto)
python ingesta/ingestar.py

# Opción 2: Construcción y ejecución en contenedor aislado (desde psets/proyecto)
docker build -t oralsolutions-ingesta .
docker run --rm -v "${PWD}\data\raw:/app/data/raw" oralsolutions-ingesta
```

## Cómo correr el pipeline de datos

Implementa un pipeline ELT reproducible que procesa los **11 archivos CSV** mediante **Kestra → Snowflake Raw → dbt (Bronze, Silver y Gold) → Apache Spark → Snowflake OBT**, además de incluir una cadena local de calidad y warehouse en **DuckDB** (`calidad/` y `warehouse/construir_warehouse.py`). Salvo los scripts SQL (que se ejecutan en **Snowsight**), todos los comandos se ejecutan desde **`psets/proyecto/`**.

### 1. Requisitos previos y configuración en Snowflake

- **Docker Desktop** con Docker Compose y contenedores Linux (comandos escritos para PowerShell en Windows).
    
- **Python 3.11+** con dependencias instaladas (`pip install -r requirements.txt`).
    
- **Cuenta de Snowflake** con permisos `ACCOUNTADMIN` y autenticación usuario/contraseña habilitada.
    
- Los **11 archivos CSV** colocados en `data/raw/`.
    

La implementación utiliza los siguientes recursos en Snowflake (la inicialización SQL crea el warehouse, la base, los esquemas, las tablas Raw, el formato CSV y el stage, pero **no aprovisiona el usuario**):

|**Recurso**|**Nombre o requisito utilizado**|
|---|---|
|Base de datos|`ORALSOLUTIONS_DW`|
|Warehouse|`COMPUTE_WH`|
|Rol de los flujos JDBC de Kestra|`ACCOUNTADMIN`|
|Esquemas|`RAW`, `BRONZE`, `SILVER`, `GOLD`, `OBT`|

### 2. Configurar credenciales privadas

Crear los archivos locales de configuración a partir de las plantillas públicas (ignorados por `.gitignore`):

PowerShell

```
Copy-Item .env.example .env
Copy-Item infra/config/dbt/profiles.example.yml infra/config/dbt/profiles.yml
```

- **En `.env`:** completar `KESTRA_DB_PASSWORD`, `KESTRA_ADMIN_EMAIL`, `KESTRA_ADMIN_PASSWORD`, `ENV_SNOWFLAKE_URL`, `ENV_SNOWFLAKE_USER`, `SF_ACCOUNT`, `SF_USER`, `SF_WAREHOUSE=COMPUTE_WH`, `SF_DATABASE=ORALSOLUTIONS_DW`, `SF_GOLD_SCHEMA=GOLD`, `SF_OBT_SCHEMA=OBT`, `SF_ROLE=ACCOUNTADMIN`, `SECRET_SNOWFLAKE_PASSWORD` (contraseña en Base64 UTF-8) y `ENV_KESTRA_HOST_PROJECT_PATH` (ruta absoluta de `psets/proyecto/` visible para Docker, guardando `.env` en UTF-8 sin BOM con finales de línea `LF`).
    
    PowerShell
    
    ```
    # Generar SECRET_SNOWFLAKE_PASSWORD en Base64:
    python -c "import base64,getpass; print(base64.b64encode(getpass.getpass('Contraseña Snowflake: ').encode('utf-8')).decode('ascii'))"
    ```
    
- **En `infra/config/dbt/profiles.yml`:** completar `account`, `user`, `password` (texto plano, sin Base64), `role: ACCOUNTADMIN` y `warehouse: COMPUTE_WH` manteniendo el perfil `oralsolutions`, target `dev` y base `ORALSOLUTIONS_DW`.
    







































## Cómo entrenar y evaluar el modelo

[Qué notebook corre cada etapa del modelado, en qué orden, y qué necesita levantado (MLflow). Se completa con el PSet 3.]

## Modelo final

[El modelo elegido, su `run_id` en MLflow y la métrica que lo sostiene. El razonamiento completo está en `docs/decision_modelo.md`. Se completa con el PSet 3.]

## Cómo correr el servicio

[Cómo se construye y se levanta el contenedor de `servicio/`, qué versión del modelo carga desde el registro, y un ejemplo de petición con su respuesta. Se completa con el PSet 4.]
