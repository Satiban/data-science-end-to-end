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

## Cómo correr el pipeline de datos

[Los comandos, en orden y desde qué carpeta, para ir de la fuente al warehouse: levantar la infraestructura, construir la imagen, subir el flow a Kestra, limpiar, cargar y correr dbt. Cada paso dice qué archivo deja y dónde. Se completa con el PSet 2.]

## Cómo entrenar y evaluar el modelo

[Qué notebook corre cada etapa del modelado, en qué orden, y qué necesita levantado (MLflow). Se completa con el PSet 3.]

## Modelo final

[El modelo elegido, su `run_id` en MLflow y la métrica que lo sostiene. El razonamiento completo está en `docs/decision_modelo.md`. Se completa con el PSet 3.]

## Cómo correr el servicio

[Cómo se construye y se levanta el contenedor de `servicio/`, qué versión del modelo carga desde el registro, y un ejemplo de petición con su respuesta. Se completa con el PSet 4.]
