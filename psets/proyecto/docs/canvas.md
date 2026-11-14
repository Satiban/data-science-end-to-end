# Canvas de Viabilidad y Riesgos — OralSolutions

**Proyecto:** Pipeline ELT y Predicción de Abandono de Tratamientos Odontológicos (OralSolutions)  
**Fecha:** 26/10/2026  

## 1. Problema y usuario
La clínica odontológica OralSolutions enfrenta pérdidas económicas y afectaciones clínicas debido al abandono prematuro de tratamientos por parte de los pacientes, un problema que hoy se gestiona de forma puramente reactiva tras la inasistencia.

## 2. Viabilidad técnica, parte 1: predicción
Estimar la probabilidad de que un paciente activo abandone su tratamiento en los próximos 60 días (definido como no agendar o faltar a su cita de control dentro de la ventana esperada), evaluada a nivel de paciente-tratamiento activo tras cada consulta atendida.

## 3. Viabilidad técnica, parte 2: datos
Se cuenta con los datos ya acceso necesario, que consta de 11 archivos CSV del sistema de gestión de citas, fichas clínicas, pacientes, odontólogos, procedimientos y seguimientos de la clínica odontológica `data/raw/` (38,603 registros totales).

## 4. Viabilidad de negocio, parte 1: acción
El personal administrativo y clínico recibe una alerta automatizada para priorizar acciones preventivas (recordatorios personalizados y reprogramación de citas) en lugar de llamar de forma reactiva cuando el paciente ya abandonó.

## 5. Viabilidad de negocio, parte 2: juicio
El sistema actúa como una herramienta de apoyo (sistema de recomendación / priorización). El personal administrativo revisa las alertas y coordina el contacto, mientras que el odontólogo valida la pertinencia clínica y la continuidad del tratamiento.

## 6. Viabilidad de negocio, parte 3: resultado
**Métrica de negocio:** Incrementar en **10 puntos porcentuales** la tasa de continuidad de tratamientos a 60 días, comparando el grupo con seguimiento preventivo frente a la atención habitual.
**Justificación del umbral de decisión ($\ge 60\%$):** Se fija una probabilidad igual o superior al 60% para priorizar las alertas. El costo de una falsa alarma (enviar un mensaje o llamada corta de recordatorio) es sumamente bajo en comparación con el costo financiero y de salud de perder un paciente recurrente en un tratamiento de largo plazo.

## 7. Riesgos

**Riesgo 1**
- **Supuesto que rompe:** Los registros históricos de citas y tratamientos permiten construir de forma consistente el target de abandono a 60 días antes de iniciar el entrenamiento del modelo.
- **Qué evidencia confirmaría o descartaría este riesgo:** Analizar la completitud y trazabilidad temporal en Silver/Gold y verificar las fechas de seguimiento posteriores en los datos.
- **Qué tan grave sería si ocurre:** Alta. Si no es posible reconstruir el target temporalmente, el modelo predictivo carecería de variable objetivo válida.

**Riesgo 2**
- **Supuesto que rompe:** El personal administrativo y clínico de la clínica utilizará las predicciones y alertas del sistema para realizar los seguimientos preventivos en su operación diaria.
- **Qué evidencia confirmaría o descartaría este riesgo:** Evaluar la adopción mediante una prueba piloto o simulación operativa del flujo en Kestra.
- **Qué tan grave sería si ocurre:** Media. Si el equipo ignora las alertas, la predicción matemática no generará ninguna acción ni mejora en la retención de pacientes.