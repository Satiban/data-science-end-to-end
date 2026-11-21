# Propuesta de proyecto: Predicción de Abandono de Tratamientos Odontológicos — OralSolutions

**Autor:** Steve Tibán  
**Fecha:** 26/10/2026 (Actualizado en PSet 4 — 21/11/2026)

---

## 1. El problema de negocio y la métrica de éxito

La clínica odontológica **OralSolutions** pierde continuidad asistencial e ingresos recurrentes porque una alta proporción de pacientes interrumpe sus tratamientos de múltiples sesiones antes de completarlos. En el historial clínico-operativo verificado, el **61.93 %** de las sesiones activas termina en abandono a 60 días (`1,472` de `2,377` sesiones calificables en `1,287` pacientes), lo que representa hasta **$61,800 USD trimestrales** en ingresos en riesgo si no se interviene. Actualmente, el equipo administrativo contacta a los pacientes de forma puramente reactiva después de que faltan a sus citas, cuando la deserción suele ser difícil de revertir. Este proyecto está dirigido a la gerencia clínica y al equipo de recepción para anticipar qué pacientes están en riesgo y actuar antes de que abandonen su plan.

Formulado como un problema de ciencia de datos, el modelo estima, tras cada sesión clínica atendida con sesiones aún pendientes (`numero_sesion < sesiones_planificadas`), la probabilidad binaria (`abandono_60d`) de que el paciente **no asista a ninguna sesión de continuidad de su plan en los siguientes 60 días** (`1` = abandona; `0` = continúa). Técnicamente se evalúa con **PR-AUC** como métrica principal (complementada con *recall* y precisión) frente a la línea base operativa actual (regla reactiva de 14 días sin cita reprogramada) y una regla estructural (falta 1 sesión para concluir el plan). La predicción se convierte en una acción de contacto preventivo cuando supera el umbral de decisión: aunque inicialmente se propuso un umbral del **60 %** como punto de partida operativo, la fuerte asimetría de costos **40:1** entre un abandono no detectado (**`FN = $120 USD`** en ingresos perdidos) y una llamada preventiva innecesaria (**`FP = $3 USD`** en tiempo administrativo) justificó calibrarlo a la baja durante el modelado hasta **`u = 0.01`**, maximizando la detección de abandonos reales.

---

## 2. Viabilidad técnica

La predicción requiere cuatro bloques de información clínica y operativa del ecosistema de OralSolutions, todos con **acceso confirmado y autorizado** para uso analítico en formato seudonimizado dentro del repositorio local `data/raw/` (**11 archivos CSV**, `38,603` registros crudos) correspondientes a **22 meses de operación** (`2024-01-02` a `2025-11-01`):

- **Agenda y asistencia (`appointments.csv`, `missed_appointments.csv`):** Acceso confirmado. Contiene fechas programadas, asistencias, cancelaciones, reprogramaciones e inasistencias históricas necesarias para calcular la fricción previa de cada paciente.
- **Planes y sesiones clínicas (`treatment_plans.csv`, `treatment_sessions.csv`, `treatment_lines.csv`, `procedures.csv`):** Acceso confirmado. Abarca `2,500` pacientes, `3,015` planes y `6,794` sesiones registradas. Tras filtrar sesiones completadas con continuidad pendiente y aplicar un corte de 60 días (`<= 2025-11-01`) para evitar censura a la derecha, se cuenta con **`2,377` sesiones calificables** pertenecientes a **`1,287` pacientes** y **`1,576` planes**, divididas temporalmente (`2025-08-01`) en **`1,551` sesiones de entrenamiento** (`65.25 %`) y **`826` sesiones de evaluación** (`34.75 %`).
- **Contexto del paciente, odontólogo y cobertura (`patients.csv`, `dentists.csv`, `insurers.csv`, `invoices.csv`):** Acceso confirmado. Aporta edad en atención, tipo de contrato del odontólogo y cobertura aseguradora, sin incluir identificadores personales en el modelo.
- **Registros de seguimiento (`patient_followups.csv`):** Acceso confirmado y auditado. Se excluye del entrenamiento predictivo porque el **`72.49 %`** de los contactos registrados ocurre después del cierre del plan, lo que introduciría fuga temporal en el modelo.

---

## 3. Viabilidad de negocio

Hoy, recepción revisa ausencias de forma manual y reactiva después de que el paciente ya dejó de asistir. Con el sistema predictivo operando en modo **batch diario nocturno**, esa rutina cambia: cada mañana el equipo administrativo recibe una lista priorizada de pacientes con riesgo de abandono tras su última consulta atendida para ejecutar recordatorios personalizados, llamadas breves y reprogramaciones oportunas durante la jornada laboral siguiente. El volumen operativo promedio (**`~8 a 12` sesiones calificables por día hábil**, `~275` al mes) es completamente absorbible por la capacidad actual de recepción.

La decisión de contacto mantiene supervisión humana explícita (*human-in-the-loop*): el modelo funciona únicamente como herramienta de priorización y nunca cancela citas ni restringe atención. El personal administrativo decide el tono, el canal y el momento del contacto, mientras que el odontólogo interviene cuando es necesario validar la pertinencia clínica o ajustar el calendario del tratamiento.

El éxito de la intervención se mide con métricas directas de negocio y no solo técnicas: la **tasa de continuidad de tratamientos a 60 días**, el **costo total de errores** (`FN × $120 + FP × $3` USD) y el **balance neto trimestral (USD)**. Se fijó como meta elevar la continuidad a 60 días en **+10 puntos porcentuales** (del `38.07 %` histórico a `≥ 48.07 %`). Bajo una tasa conservadora de rescate efectivo del **`35 %`** por contacto preventivo (`+$39 USD` netos por abandono prevenido: `0.35 × $120 − $3`), la simulación productiva sobre los `8` lotes reales (`826` sesiones) confirma un balance neto de **`+$18,294 USD` trimestrales** (**`+$6,000 USD`** adicionales sobre la regla heurística de seguimiento) y una reducción del **`74.2 %`** en el costo total de errores (`$1,518` vs. `$5,880 USD`).

---

## 4. Riesgos principales

### Riesgo 1 — Reconstrucción temporal del target de abandono a 60 días
- **Supuesto que rompe:** Los registros clínicos permiten construir de manera consistente y libre de fuga la variable objetivo `abandono_60d` antes de entrenar el modelo.
- **Evidencia para confirmarlo o descartarlo:** Se aplica un protocolo de verificación en cuatro pasos previo al entrenamiento: (1) auditar integridad referencial y cronológica entre `appointments`, `treatment_plans` y `treatment_sessions`, excluyendo `patient_followups` por fuga post-cierre; (2) filtrar únicamente sesiones completadas con sesiones pendientes (`numero_sesion < sesiones_planificadas`); (3) aplicar un corte temporal de 60 días respecto a la fecha máxima del historial (`<= 2025-11-01`) para eliminar censura a la derecha, verificando estabilidad en la tasa de abandono final (`63.7 %` vs. `61.4 %`); y (4) confirmar `0` valores nulos en `abandono_60d` y ausencia de columnas futuras.
- **Gravedad:** **Alta.** Si el target no pudiera reconstruirse con rigor temporal, cualquier modelo entrenado aprendería señales ficticias o sesgadas, obligando a estandarizar los registros antes de avanzar.

### Riesgo 2 — Adopción operativa por parte del equipo de la clínica
- **Supuesto que rompe:** El personal administrativo y clínico consultará y utilizará las alertas de riesgo en su rutina diaria para priorizar llamadas preventivas.
- **Evidencia para confirmarlo o descartarlo:** Ejecutar una prueba piloto operativa con el panel de priorización de recepción (tablero de seguimiento) midiendo la proporción de alertas revisadas y gestionadas por jornada hábil.
- **Gravedad:** **Media.** Si las alertas se ignoran, la precisión del modelo no se traduce en retención real; se mitiga simplificando la interfaz a una acción concreta (`contactar` / `no_contactar`) y capacitando al personal.

### Riesgo 3 — Efectividad real de la intervención preventiva en la continuidad
- **Supuesto que rompe:** Contactar anticipadamente a los pacientes en riesgo logra una tasa de rescate suficiente (al menos `35 %`) para mejorar la continuidad a 60 días frente al proceso habitual.
- **Evidencia para confirmarlo o descartarlo:** Contrastar mediante un piloto controlado (prueba A/B) la tasa real de continuidad a 60 días y el retorno neto entre pacientes con seguimiento preventivo y pacientes bajo el proceso habitual, registrando el resultado real de cada llamada.
- **Gravedad:** **Alta.** Si el contacto temprano no mejora la asistencia, se deberán ajustar el guion de seguimiento, los horarios de reprogramación y el umbral de decisión.