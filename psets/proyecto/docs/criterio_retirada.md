# Ética Operativa y Criterios de Retirada — OralSolutions

## 1. Ética Operativa y Distribución de Costos

### Quién asume el costo de cada error
* **Falso Negativo (`FN = $120 USD`):** Lo asumen conjuntamente el **paciente** (interrupción de un tratamiento odontológico en curso con riesgo de complicaciones clínicas) y la **clínica** (pérdida del ingreso recurrente del plan).
* **Falso Positivo (`FP = $3 USD`):** Lo asume el **equipo de recepción** (tiempo de una llamada o mensaje preventivo adicional) y, de forma marginal, el paciente al recibir un recordatorio cordial.
* **Justificación ética del umbral (`u = 0.01`):** Dada la asimetría `40 : 1` y el carácter no invasivo de la intervención (un recordatorio preventivo, nunca una negación de servicio ni una decisión clínica automática), priorizar `Recall = 98.64%` protege la continuidad clínica sin penalizar al paciente.

### Desempeño por subgrupo operativo
El modelo clasifica sesiones según tipo de procedimiento (`complejidad_proc`):
* **Procedimientos restaurativos cortos (`EXTRACT`, `FILL1`, `FILL2`):** Presentan tasas históricas de abandono de `71.0%–100.0%`, por lo que el servicio concentra allí una tasa de decisión `contactar` cercana al `100%`.
* **Tratamientos extensos o especializados (`ROOT`, `CROWN`, `WHITEN`):** Presentan abandono de `52.4%–53.7%`, donde el modelo discrimina entre sesiones tempranas (`no_contactar`) y sesiones con mayor avance o fricción previa (`contactar`).
* **Control de equidad:** No se utilizan variables sensibles ni discriminatorias (ningún identificador personal entra al modelo); la única variable demográfica (`edad_en_atencion`) aporta una importancia marginal (`< 0.01%`) y se vigila con `PSI` en `monitoreo/deriva.py`.

### Vigencia del juicio humano (PSet 1)
El juicio humano definido en el PSet 1 **sigue plenamente vigente**: el modelo nunca cancela citas, no altera agendas ni emite diagnósticos; únicamente ordena una lista diaria de prioridad para que recepción decida el tono y canal del recordatorio, y el equipo de datos aprueba manualmente cualquier promoción de modelo mediante la tarea `Pause` en `orquestacion/reentrenamiento.yml`.

---

## 2. Criterios de Retirada y Apagado Controlado

El modelo `@champion` deja de operar automáticamente (activando el modo respaldo hacia la línea base `Regla1SesionRestante`) o se retira de producción si se cumple cualquiera de las siguientes **4 condiciones observables y medibles** registradas por `monitoreo/` y `GET /metricas`:

| # | Condición observable | Métrica y fuente | Umbral de disparo | Acción obligatoria |
|---|---|---|---|---|
| **1** | **Caída sostenida de discriminación (deriva conceptual)** | `PR-AUC` por lote en `docs/monitoreo.csv` | `PR-AUC < 0.960` en **2 lotes etiquetados consecutivos** (o caída por debajo de la línea base `Regla1SesionRestante`, `0.9642`) | Activar modo respaldo vía `POST /admin/respaldo` (`activar=true`) y abrir investigación de cambio de comportamiento clínico antes de reentrenar. |
| **2** | **Pérdida de valor financiero frente a la línea base** | `costo_modelo_usd` vs. `costo_regla_1_sesion_usd` en `docs/monitoreo.csv` | Costo de errores del modelo **superior** al de la línea base operativa en **2 lotes consecutivos** | Retirar temporalmente el modelo ML, operar con la regla determinista de respaldo y reevaluar el umbral `u = 0.01` y los costos `FN/FP`. |
| **3** | **Deriva severa de entradas o rotura de esquema** | `PSI` máximo y `% faltantes` en `monitoreo/deriva.py` | `PSI > 0.30` acompañado de caída en `PR-AUC`, o **`> 5%` de valores faltantes** / categorías desconocidas en `codigo_procedimiento` | Detener inferencia batch en Kestra, auditar el pipeline ELT (`flow_proyecto.yml` / dbt) y mantener respaldo hasta restaurar calidad de datos. |
| **4** | **Degradación operativa del servicio** | Tasa de errores HTTP (`4xx/5xx`) y latencia `p95` en `GET /metricas` / `GET /alertas` | Tasa de error `> 5%` o `latencia_p95_ms > 250 ms` sostenidos en el lote nocturno, o falla de carga desde MLflow | Fallback automático inmediato a `Regla1SesionRestante` (`uso_respaldo = true`) y rollback del alias `@champion` en MLflow sin reconstruir Docker. |

---

## 3. Procedimiento del Interruptor de Respaldo

El servicio `servicio/api.py` implementa dos mecanismos verificados por `servicio/test_api.py`:
1. **Respaldo automático (*fallback*):** Si el servidor MLflow no responde o el artefacto no carga, `POST /predecir` responde `200 OK` usando `Regla1SesionRestante` y marcando `"uso_respaldo": true` y `"version_modelo": "fallback-regla-1-sesion"`.
2. **Interruptor manual protegido:** Un operador autorizado puede forzar el modo respaldo en caliente sin reiniciar el contenedor (o mediante variable de entorno `MODO_RESPALDO=true`):

```bash
curl -X POST http://127.0.0.1:8000/admin/respaldo \
  -H "Content-Type: application/json" \
  -H "x-admin-token: oralsolutions-admin-token" \
  -d '{"activar": true, "motivo": "Criterio de retirada activado por deriva conceptual"}'
```