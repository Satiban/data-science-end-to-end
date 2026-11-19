# Estrategia de Despliegue, Versionado y Métricas del Servicio — OralSolutions

## 1. Patrón de Despliegue: Batch Diario

Se elige el patrón de despliegue **batch diario** (ejecución nocturna programada a las `02:00` mediante Kestra) sobre el servicio de inferencia expuesto en `servicio/api.py`, descartando el patrón *online* en tiempo real en ventanilla.

### Justificación cuantitativa desde el caso de uso
* **Latencia que tolera la acción de negocio:** El modelo predice abandono de tratamientos odontológicos en un horizonte de **60 días** tras el cierre de una sesión atendida (`numero_sesion < sesiones_planificadas`). La acción habilitada es una llamada telefónica o recordatorio personalizado realizado por el equipo de recepción durante el horario laboral del día siguiente. La predicción debe estar disponible en menos de **24 horas** (antes de las `08:00` de la jornada siguiente), no en milisegundos.
* **Frecuencia de llegada de nuevos datos:** El pipeline ELT (`orquestacion/flow_proyecto.yml`) ingesta las tablas operativas y reconstruye `OBT_RIESGO_ABANDONO` una vez al día en ventana nocturna.
* **Volumen diario de predicciones:** El histórico limpio abarca `2,377` sesiones calificables en ~22 meses (`~8` a `12` sesiones por día hábil, `~275` sesiones/mes en el trimestre *hold-out*). La inferencia del trimestre completo tarda `< 6 ms` (`< 0.01 ms` por paciente).
* **Costo de actuar con una predicción desactualizada:** En un horizonte de 60 días, diferir la alerta unas horas (del cierre de la consulta a la mañana siguiente) no altera la probabilidad de retención ni genera pérdida clínica adicional; en cambio, omitir una alerta (`FN = $120 USD`) cuesta **40 veces más** que una llamada preventiva (`FP = $3 USD`).

### Qué se pierde con el patrón descartado (*Online*) y cuándo cambiaría la decisión
* **Qué se pierde / sobrecosto de elegir *online*:** Desplegar inferencia síncrona en tiempo real acoplada al sistema de agenda de recepción exigiría alta disponibilidad `24/7`, monitoreo de latencia sub-segundo en horario de consulta y consultas transaccionales en vivo a Snowflake para calcular variables históricas (`cancelaciones_previas`, `inasistencias_previas`, `dias_desde_inicio_plan`), añadiendo complejidad operativa sin mejorar la tasa de retención a 60 días.
* **Qué tendría que cambiar para pasar a *online*:** Si OralSolutions incorporara una intervención inmediata **antes de que el paciente salga de la clínica** (por ejemplo, ofrecer un descuento automático en caja o agendar la siguiente cita en pantalla con alerta instantánea al recepcionista en `< 500 ms` tras cerrar la atención), el patrón adecuado pasaría a ser **online**.

---

## 2. Arquitectura del Servicio, Registro y Versionado

* **Fuente de verdad:** MLflow Model Registry (`oralsolutions-modelo`) levantado en `infra/docker-compose.yml` (`http://mlflow:5000`).
* **Modelo activo (`@champion`):** `oralsolutions-modelo` **versión 7** (`FINAL_Red_Neuronal`, `run_id = 169e8821e2c54761bf602b21f86aec93`, `PR-AUC test = 0.98269`, umbral calibrado `u = 0.01`).
* **Modelo de respaldo en registro (`@challenger`):** `oralsolutions-modelo` **versión 8** (`Tuning_LogisticRegression`, `run_id = 92446a9861994d22a0a7431b389f1eb1`, `PR-AUC test = 0.98218`).
* **Carga desacoplada:** El contenedor `api` (`servicio/Dockerfile`) importa las transformaciones directamente desde `modelado/pipeline_proyecto.py` y carga `models:/oralsolutions-modelo@champion`. Cambiar de versión no requiere reconstruir la imagen Docker.
* **Trazabilidad:** Cada llamada a `POST /predecir` genera un `id_prediccion` (UUID), registra entradas, probabilidad, decisión (`contactar`/`no_contactar`), `version_modelo`, `run_id`, bandera `uso_respaldo` y `latencia_ms` en la tabla `PREDICCIONES` de Snowflake (y log estructurado local).

### Regla de promoción (`@challenger` → `@champion`)
Un modelo `@challenger` solo reemplaza al `@champion` si cumple **simultáneamente** las tres condiciones evaluadas sobre el mismo lote etiquetado más reciente (no visto en entrenamiento por ninguno de los dos):
1. **Mejora en métrica de negocio:** Reduce el **costo total de errores** (`FN × $120 + FP × $3`) respecto al `@champion` actual (o eleva el balance neto operativo).
2. **Estabilidad técnica:** Su `PR-AUC` en el lote de evaluación no cae por debajo del `@champion` en más de una desviación estándar de la validación cruzada temporal (`σ_CV = 0.00342`).
3. **Aprobación humana explícita:** Supera la tarea en pausa de revisión manual en el flujo `reentrenamiento.yml` de Kestra.

### Procedimiento de cambio de versión y Rollback
Para promover una nueva versión o revertir a una versión anterior **sin reconstruir la imagen**:
1. En el Model Registry de MLflow (interfaz web o `MlflowClient`), reasignar el alias `@champion` al número de versión deseado (`client.set_registered_model_alias("oralsolutions-modelo", "champion", "<version>")`).
2. Consultar `GET /modelo`: el servicio detecta el cambio de versión en MLflow, recarga el artefacto en memoria y devuelve el nuevo `version` y `run_id`.
3. Ante una falla crítica del servidor MLflow o degradación severa, la API activa automáticamente (o vía interruptor protegido `POST /admin/respaldo` / variable `MODO_RESPALDO=true`) la línea base de negocio (`Regla1SesionRestante`), devolviendo `"uso_respaldo": true`.

### Por qué el código tiene despliegue continuo (`cd.yml`) pero el modelo no
El código de la API se publica automáticamente en GitHub Container Registry (`cd.yml`) tras pasar las 14 pruebas automáticas (`ci.yml`) porque su comportamiento es determinista y verificable mediante pruebas unitarias y de contrato. En cambio, **un modelo de ML no se promueve automáticamente** porque sus pesos dependen de datos recientes que pueden contener deriva no diagnosticada, cambios estacionales o sesgos por subgrupo; promoverlo sin aprobación humana podría disparar falsos negativos (`$120 USD` cada uno) o saturar a recepción con llamadas innecesarias.

---

## 3. Métricas del Servicio y del Modelo

El endpoint `GET /metricas` y la tabla `MONITOREO` de Snowflake vigilan tres capas justificadas por la operación de OralSolutions:

| Capa | Métricas registradas | Por qué se eligieron en OralSolutions |
|---|---|---|
| **Sistema** | Latencia `p50` y `p95` (ms), tasa de errores `4xx` y `5xx`, volumen de solicitudes, disponibilidad (`/salud`). | Garantizan que el lote nocturno complete antes de las `08:00` y permiten detectar contratos rotos (`422`) cuando el sistema de agenda clínica cambia formatos o códigos de procedimiento. |
| **Modelo (sin target inmediato)** | Distribución de probabilidades predichas, tasa de decisión `contactar` vs. `no_contactar`. | Como el target real (`abandono_60d`) tarda **60 días** en confirmarse, un salto abrupto en la tasa de alertas `contactar` es la mejor señal temprana de degradación operativa antes de disponer de etiquetas. |
| **Modelo (con target a 60 días)** | `PR-AUC` por lote, `Recall`, `Precisión`, **Costo de errores (`FN×$120 + FP×$3`)** y **Balance neto (USD)**. | Miden directamente la capacidad de discriminación y el impacto financiero real del modelo frente a la línea base operativa. |
| **Datos** | Porcentaje de faltantes por feature, valores fuera de rango, categorías no vistas, **PSI** y pruebas KS / Chi-cuadrado. | Detectan deriva en las variables que explican el `98%` de la señal del modelo (`progreso_plan`, `sesiones_planificadas`, `numero_sesion`) antes de que caiga el desempeño. |