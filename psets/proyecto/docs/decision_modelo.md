# Decisión del Modelo Final — OralSolutions (`abandonos_60d`)

Este documento resume la evidencia técnica y financiera que respalda el paso a producción del modelo de predicción de abandono de tratamientos odontológicos a 60 días (`abandono_60d`), ejecutado al cierre de cada sesión clínica atendida (`fecha_realizada`) cuando el paciente aún tiene sesiones pendientes en su plan (`numero_sesion < sesiones_planificadas`).

---

## 1. Modelo Elegido y Registro en MLflow

* **Modelo ganador (`@champion`):** Pipeline completo de scikit-learn (`ColumnTransformer` + `MLPClassifier` con `alpha = 0.00338`, `learning_rate_init = 3.49e-4`, `hidden_layer_sizes = (128, 64)`, `max_iter = 400`, `random_state = 42`).
* **Experimento en MLflow:** `OralSolutions` (`modelado/experimentos_proyecto.ipynb`, exportado sin duplicados a `modelado/corridas_proyecto.csv` con 101 corridas).
* **Corrida final oficial:** `FINAL_Red_Neuronal` con **`run_id = 169e8821e2c54761bf602b21f86aec9`** y tag `candidato = final`.
* **Model Registry:** Registrado como **`oralsolutions-modelo`** (**versión 7**, alias **`@champion`**). Al recargar `models:/oralsolutions-modelo@champion` en `modelado/validacion_proyecto.ipynb` se reproduce exactamente **`PR-AUC = 0.98269`** en prueba.
* **Segundo mejor modelo (`@challenger`):** `Tuning_LogisticRegression` (`C = 73.9`, `class_weight = None`), **`run_id = 92446a9861994d22a0a7431b389f1eb1`**, registrado como **`oralsolutions-modelo`** (**versión 8**, alias **`@challenger`**).

---

## 2. Comparación Contra Líneas Base y Candidatos

Todos los modelos se entrenaron y evaluaron bajo exactamente las mismas condiciones:
* **Dataset y huella:** `data/processed/obt_riesgo_abandono.csv` (2,377 sesiones limpias, 21 columnas, 0 nulos; **`SHA-256 = 937af6f343e5de34e3e6b07cd211ebde6732221e73c53d2ec47d0e26a767cf60`**).
* **Partición temporal única (`FECHA_CORTE = 2025-08-01`):** `1,551` sesiones históricas para entrenamiento (`65.25%`, abandono `61.70%`) y `826` sesiones recientes (`2025-08-01` a `2025-11-01`) como prueba *hold-out* (`34.75%`, abandono `62.35%`).
* **Preprocesamiento sin fuga (`modelado/pipeline_proyecto.py`):** Imputación por mediana + `RobustScaler` en 10 variables numéricas e imputación por moda + `OneHotEncoder(handle_unknown="ignore")` en 3 categóricas nominales, ajustado únicamente con entrenamiento (23 columnas finales).

| Modelo | Familia | PR-AUC Train | PR-AUC CV (Media ± Std) | PR-AUC Test | Brecha Train–Test | Segundos |
|---|---|---:|---:|---:|---:|---:|
| `Baseline_Dummy_Mayoritaria` | Línea Base | 0.6170 | 0.6256 ± 0.0248 | 0.6235 | -0.0065 | 0.06 |
| `Baseline_Regla_Negocio_14d` | Línea Base | 0.6376 | — | 0.6551 | -0.0176 | 0.02 |
| `Baseline_Regla_1_Sesion` | Línea Base | 0.9628 | — | 0.9642 | -0.0014 | 0.02 |
| `RandomForest_default` | Bagging | 1.0000 | 0.9797 ± 0.0041 | 0.9814 | +0.0185 | 0.40 |
| `LogisticRegression_default` | Lineal Reg. | 0.9837 | 0.9817 ± 0.0044 | 0.9816 | +0.0021 | 0.08 |
| `HistGradientBoosting_default` | Boosting | 0.9998 | 0.9806 ± 0.0054 | 0.9843 | +0.0155 | 0.39 |
| `MLPClassifier_default` | Red Neuronal | 0.9944 | 0.9826 ± 0.0042 | 0.9833 | +0.0111 | 3.48 |
| **`Tuning_LogisticRegression` (`@challenger`)** | **Lineal Ajustado** | **0.9853** | **0.98298 ± 0.00461** | **0.98218** | **+0.0031** | **0.08** |
| **`FINAL_Red_Neuronal` (`@champion`)** | **Red Ajustada** | **0.9963** | **0.98330 ± 0.00342** | **0.98269** | **+0.0136** | **3.48** |

*(Nota: En una evaluación exploratoria de 5.ª familia con LLM mediante simulación determinista de few-shot prompting sobre 30 filas reales de `X_test`, el LLM obtuvo `PR-AUC = 0.9498` frente a `1.0000` de `HistGradientBoosting` en las mismas filas, descartándose por latencia ~0.45 s/fila, costo variable por tokens y privacidad clínica).*

---

## 3. Validación Cruzada: ¿Es Real la Diferencia con el Segundo Mejor?

Dado que el modelo predice deserción futura y el **73.7 %** de las sesiones pertenecen a pacientes recurrentes (`1,287` pacientes en `1,576` planes), el esquema principal es **`TimeSeriesSplit(n_splits=5)`** en pliegues expansivos sobre entrenamiento, contrastado contra **`GroupKFold(n_splits=5)`** por `paciente_key` y **`KFold(n_splits=5, shuffle=True)`** aleatorio:

| Esquema de Validación Cruzada | Modelo | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Media ± Std |
|---|---|---:|---:|---:|---:|---:|---:|
| **`TimeSeriesSplit(5)` (Principal)** | **`@champion` (MLP)** | 0.98946 | 0.98393 | 0.97940 | 0.98253 | 0.98119 | **0.98330 ± 0.00342** |
| **`TimeSeriesSplit(5)` (Principal)** | **`@challenger` (LogReg)** | 0.98962 | 0.98396 | 0.97519 | 0.98261 | 0.98352 | **0.98298 ± 0.00461** |
| `GroupKFold(5)` (por paciente) | `@champion` (MLP) | — | — | — | — | — | **0.98249 ± 0.00301** |
| `GroupKFold(5)` (por paciente) | `@challenger` (LogReg) | — | — | — | — | — | **0.98232 ± 0.00322** |
| `KFold(5, shuffle)` (aleatorio) | `@champion` (MLP) | — | — | — | — | — | **0.98351 ± 0.00290** |
| `KFold(5, shuffle)` (aleatorio) | `@challenger` (LogReg) | — | — | — | — | — | **0.98325 ± 0.00310** |

* **Conclusión estadística:** La diferencia promedio en CV temporal a favor de `@champion` (**`+0.00032`**) **es menor que la desviación estándar entre pliegues (`0.00342`)**, y la red neuronal supera a la regresión logística únicamente en 1 de los 5 pliegues (Fold 3: `0.97940` vs. `0.97519`). Además, `GroupKFold` y `KFold` quedan a `≤ 0.001` del esquema temporal, por lo que no se detecta diferencia práctica significativa entre esquemas. Se mantiene `FINAL_Red_Neuronal` como `@champion` porque la selección se fijó *a priori* sobre `pr_auc_cv_mean` antes de evaluar costos y presenta menor dispersión entre pliegues (`0.00342` vs. `0.00461`), conservando `Tuning_LogisticRegression` como respaldo inmediato (`@challenger`).

---

## 4. Error Más Caro, Métrica de Negocio y Calibración de Umbral

* **Asimetría de costos (40 : 1):**
  * **Falso Negativo (`FN = $120 USD`):** Error más costoso; paciente que abandona su tratamiento sin recibir alerta preventiva, perdiendo el ingreso promedio de sus sesiones pendientes.
  * **Falso Positivo (`FP = $3 USD`):** Costo operativo de una llamada o recordatorio personalizado de recepción a un paciente que igual habría asistido.
  * **Rescate efectivo (`TP`):** Con una tasa conservadora de retención del `35%` tras el contacto preventivo, cada alerta acertada genera un beneficio esperado de `0.35 × $120 − $3 = +$39 USD`.
* **Resultados en prueba (`X_test`, 826 sesiones):**

| Política de Decisión | PR-AUC Test | Recall | Precisión | Costo Errores (`FN×120 + FP×3`) | Balance Neto |
|---|---:|---:|---:|---:|---:|
| Llamar a todos (sin modelo) | — | 100.00 % | 62.35 % | $933 | $19,152 |
| Regla estructural «falta 1 sesión» | 0.9642 | 90.49 % | 100.00 % | $5,880 | $12,294 |
| `@champion` MLP (`u = 0.60`, inicial PSet 1) | 0.98269 | 91.26 % | 97.71 % | $5,433 | $12,897 |
| `@champion` MLP (`u = 0.10`) | 0.98269 | 95.15 % | 79.55 % | $3,378 | $15,732 |
| **`@champion` MLP (`u = 0.01`, calibrado)** | **0.98269** | **98.64 %** | **69.21 %** | **$1,518** | **$18,294** |
| `@challenger` Logística (`u = 0.10`) | 0.98218 | 98.25 % | 70.28 % | $1,722 | $18,012 |
| `@challenger` Logística (`u = 0.01`) | 0.98218 | 99.81 % | 63.46 % | $1,008 | $19,038 |

Calibrar el umbral desde `0.60` hasta **`u = 0.01`** recorta el costo de errores del `@champion` en un **72.1 %** (de `$5,433` a **`$1,518 USD`**) y eleva el balance neto trimestral a **`$18,294 USD`** (`+$5,397 USD` respecto al umbral inicial). Aunque la regresión logística a `u = 0.01` logra un costo marginalmente menor (`$1,008 USD`), lo hace a costa de alertar prácticamente a toda la base (`Precision = 63.46%` frente a `62.35%` de prevalencia), mientras que el `@champion` conserva mayor selectividad operativa (`Precision = 69.21%` en `u = 0.01` y `79.55%` en `u = 0.10`).

---

## 5. Costo Computacional y Explicabilidad

* **Costo de entrenamiento e inferencia:** `FINAL_Red_Neuronal` entrena en **`3.48 s`** (frente a `0.08 s` de la regresión logística) y predice el lote completo de 826 sesiones en **`< 6 ms`** (`< 0.01 ms` por consulta), apto para inferencia en tiempo real al cierre de cada cita sin GPU.
* **Explicabilidad:** A diferencia de la regresión logística (que ofrece coeficientes directos por variable), la red neuronal se audita mediante **importancia por permutación sobre PR-AUC** en prueba, donde tres variables explican el **98.0 %** de la caída positiva:
  1. `progreso_plan` (`numero_sesion / sesiones_planificadas`): **`-0.2488`**
  2. `sesiones_planificadas`: **`-0.0218`**
  3. `numero_sesion`: **`-0.0058`**

---

## 6. Reproducibilidad Exacta

Para que cualquiera obtenga exactamente **`PR-AUC = 0.98269`** en prueba:

1. **Qué se necesita:**
   * Archivo limpio `psets/proyecto/data/processed/obt_riesgo_abandono.csv` con huella **`SHA-256 = 937af6f343e5de34e3e6b07cd211ebde6732221e73c53d2ec47d0e26a767cf60`**.
   * Script `psets/proyecto/modelado/pipeline_proyecto.py` con corte temporal fijo **`FECHA_CORTE = "2025-08-01"`** y semilla **`SEED = 42`**.
   * Servicio de MLflow levantado desde `psets/proyecto/infra/docker-compose.yml` (`http://127.0.0.1:5000`) o recuperación directa del artefacto registrado.
2. **Qué quedó registrado en MLflow (verificable en `modelado/corridas_proyecto.csv`):**
   * Parámetros: `tabla_origen = obt_riesgo_abandono.csv`, `fecha_corte = 2025-08-01`, `semilla = 42`, `hash_dataset = 937af6f343e5de34...`, `alpha = 0.00338`, `learning_rate_init = 0.000349`, `hidden_layer_sizes = (128, 64)`.
   * Tags y artefactos: `fase = final`, `familia = Red_Neuronal`, `candidato = final`, `git_commit`, firma del modelo y el `Pipeline` completo serializado (`mlflow.sklearn.log_model`).
3. **Comando de verificación:**
   ```python
   import mlflow.sklearn
   from pipeline_proyecto import cargar_y_dividir

   _, X_test, _, y_test, _ = cargar_y_dividir()
   modelo = mlflow.sklearn.load_model("models:/oralsolutions-modelo@champion")