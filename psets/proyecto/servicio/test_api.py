"""
Pruebas automáticas del servicio de predicción (OralSolutions).

Cubre:
1. Contrato HTTP y validación Pydantic (200 válido; 422 por campo faltante, tipo erróneo,
   categoría desconocida o regla de dominio violada).
2. Modelo: el artefacto exportado desde MLflow reproduce PR-AUC = 0.98269 sobre la muestra fija.
3. Comportamiento de negocio: 2 invariantes del dominio odontológico.
4. Respaldo (fallback automático si el modelo no carga + interruptor manual protegido).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.metrics import average_precision_score

# Configurar modo local (fixture exportado desde MLflow) antes de importar la app
os.environ["USAR_MODELO_LOCAL"] = "true"
os.environ["REGISTRAR_SNOWFLAKE"] = "false"

from modelado.pipeline_proyecto import FEATURES_FINALES, TARGET, construir_features
from servicio import api

BASE_FIXTURES = Path(__file__).resolve().parent / "fixtures"
MUESTRA_TEST = BASE_FIXTURES / "muestra_test.csv"
PR_AUC_ESPERADO_MLFLOW = 0.98269
TOLERANCIA_PR_AUC = 0.0005

PAYLOAD_VALIDO = {
    "duracion_estimada_min": 75,
    "numero_sesion": 1,
    "sesiones_planificadas": 3,
    "cancelaciones_previas": 0,
    "inasistencias_previas": 0,
    "dias_desde_inicio_plan": 14,
    "edad_en_atencion": 42,
    "codigo_procedimiento": "CROWN",
    "odontologo_key": "2",
}


@pytest.fixture()
def client(tmp_path: Path):
    """Levanta TestClient con el modelo local cargado y log aislado en carpeta temporal."""
    api.RUTA_LOG_PREDICCIONES = tmp_path / "predicciones_test.csv"
    api.estado.modo_respaldo = False
    api.cargar_modelo()
    with TestClient(api.app) as c:
        yield c
    api.estado.modo_respaldo = False
    api.cargar_modelo()


# ---------------------------------------------------------------------------
# 1. Pruebas de contrato
# ---------------------------------------------------------------------------
def test_contrato_entrada_valida_devuelve_200(client: TestClient) -> None:
    resp = client.post("/predecir", json=PAYLOAD_VALIDO)
    assert resp.status_code == 200

    body = resp.json()
    for campo in (
        "id_prediccion",
        "probabilidad",
        "decision",
        "accion",
        "umbral_aplicado",
        "version_modelo",
        "run_id",
        "uso_respaldo",
        "latencia_ms",
        "timestamp",
    ):
        assert campo in body

    assert 0.0 <= body["probabilidad"] <= 1.0
    assert body["decision"] in {"contactar", "no_contactar"}
    assert body["uso_respaldo"] is False
    assert body["version_modelo"] == "7"


def test_contrato_campo_faltante_devuelve_422(client: TestClient) -> None:
    incompleto = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "edad_en_atencion"}
    resp = client.post("/predecir", json=incompleto)
    assert resp.status_code == 422
    assert "edad_en_atencion" in resp.text


def test_contrato_tipo_incorrecto_devuelve_422(client: TestClient) -> None:
    tipo_malo = {**PAYLOAD_VALIDO, "duracion_estimada_min": "sesenta_minutos"}
    resp = client.post("/predecir", json=tipo_malo)
    assert resp.status_code == 422
    assert "duracion_estimada_min" in resp.text


def test_contrato_categoria_desconocida_devuelve_422(client: TestClient) -> None:
    cat_invalida = {**PAYLOAD_VALIDO, "codigo_procedimiento": "IMPLANTE_DESCONOCIDO"}
    resp = client.post("/predecir", json=cat_invalida)
    assert resp.status_code == 422
    assert "codigo_procedimiento" in resp.text


def test_contrato_regla_sesiones_invalida_devuelve_422(client: TestClient) -> None:
    # No se permite predecir cuando el plan ya llegó a la última sesión
    sin_pendientes = {**PAYLOAD_VALIDO, "numero_sesion": 3, "sesiones_planificadas": 3}
    resp = client.post("/predecir", json=sin_pendientes)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 2. Prueba de reproducibilidad del modelo registrado
# ---------------------------------------------------------------------------
def test_modelo_reproduce_metrica_mlflow(client: TestClient) -> None:
    assert MUESTRA_TEST.exists(), f"Falta la muestra fija de validación: {MUESTRA_TEST}"
    assert api.estado.modelo_cargado and api.estado.modelo is not None

    df = pd.read_csv(MUESTRA_TEST)
    df_feat = construir_features(df)
    X_eval = df_feat[FEATURES_FINALES]
    y_eval = df[TARGET].astype(int)

    probs = api.estado.modelo.predict_proba(X_eval)[:, 1]
    pr_auc = float(average_precision_score(y_eval, probs))

    assert abs(pr_auc - PR_AUC_ESPERADO_MLFLOW) <= TOLERANCIA_PR_AUC, (
        f"PR-AUC obtenido ({pr_auc:.5f}) difiere de MLflow ({PR_AUC_ESPERADO_MLFLOW:.5f}) "
        f"más allá de ±{TOLERANCIA_PR_AUC}"
    )


# ---------------------------------------------------------------------------
# 3. Pruebas de comportamiento de negocio (dominio OralSolutions)
# ---------------------------------------------------------------------------
def test_negocio_mayor_progreso_hacia_ultima_sesion_aumenta_riesgo(client: TestClient) -> None:
    """
    Hallazgo clave del EDA/PSet 3: en planes de 4 sesiones, avanzar de la sesión 1
    (progreso 0.25) a la penúltima sesión 3 (progreso 0.75, falta 1 sesión) debe
    incrementar la probabilidad predicha de abandono.
    """
    temprano = {**PAYLOAD_VALIDO, "numero_sesion": 1, "sesiones_planificadas": 4}
    penultima = {**PAYLOAD_VALIDO, "numero_sesion": 3, "sesiones_planificadas": 4}

    p_temprano = client.post("/predecir", json=temprano).json()["probabilidad"]
    p_penultima = client.post("/predecir", json=penultima).json()["probabilidad"]

    assert p_penultima > p_temprano, (
        f"Se esperaba mayor riesgo al acercarse al cierre del plan: {p_penultima} vs {p_temprano}"
    )


def test_negocio_paciente_critico_dispara_alerta_contactar(client: TestClient) -> None:
    """
    Un paciente en procedimiento restaurativo corto (FILL1), con fricción previa alta
    (cancelaciones e inasistencias) y a 1 sesión de finalizar debe recibir decisión 'contactar'.
    """
    caso_critico = {
        "duracion_estimada_min": 45,
        "numero_sesion": 2,
        "sesiones_planificadas": 3,
        "cancelaciones_previas": 2,
        "inasistencias_previas": 2,
        "dias_desde_inicio_plan": 60,
        "edad_en_atencion": 38,
        "codigo_procedimiento": "FILL1",
        "odontologo_key": "1",
    }
    body = client.post("/predecir", json=caso_critico).json()
    assert body["decision"] == "contactar"
    assert body["probabilidad"] >= 0.80


# ---------------------------------------------------------------------------
# 4. Pruebas de respaldo (fallback automático) e interruptor operativo
# ---------------------------------------------------------------------------
def test_fallback_cuando_modelo_no_carga(client: TestClient) -> None:
    api.estado.modelo = None
    api.estado.modelo_cargado = False

    # Caso con 1 sesión restante -> regla de respaldo devuelve 0.99 y contactar
    caso_1_restante = {**PAYLOAD_VALIDO, "numero_sesion": 2, "sesiones_planificadas": 3}
    resp = client.post("/predecir", json=caso_1_restante)
    assert resp.status_code == 200
    body = resp.json()

    assert body["uso_respaldo"] is True
    assert body["version_modelo"] == "fallback-regla-1-sesion"
    assert body["probabilidad"] == 0.99
    assert body["decision"] == "contactar"


def test_interruptor_respaldo_protegido(client: TestClient) -> None:
    # Sin token válido -> 401
    resp_no_auth = client.post(
        "/admin/respaldo",
        json={"activar": True, "motivo": "Prueba sin token"},
        headers={"x-admin-token": "token-invalido"},
    )
    assert resp_no_auth.status_code == 401

    # Con token válido -> activa respaldo y /predecir lo refleja
    resp_ok = client.post(
        "/admin/respaldo",
        json={"activar": True, "motivo": "Degradación detectada en monitoreo"},
        headers={"x-admin-token": api.ADMIN_TOKEN},
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["modo_respaldo"] is True

    pred = client.post("/predecir", json=PAYLOAD_VALIDO).json()
    assert pred["uso_respaldo"] is True