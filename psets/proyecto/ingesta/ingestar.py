import time
from pathlib import Path

ARCHIVOS_ESPERADOS = [
    "appointments.csv",
    "dentists.csv",
    "insurers.csv",
    "invoices.csv",
    "missed_appointments.csv",
    "patient_followups.csv",
    "patients.csv",
    "procedures.csv",
    "treatment_lines.csv",
    "treatment_plans.csv",
    "treatment_sessions.csv",
]


def verificar_ingesta(ruta_raw: Path, max_reintentos: int = 3, espera_seg: int = 5) -> None:
    """Verifica con reintentos la disponibilidad de los 11 archivos CSV en data/raw/."""
    ruta_raw.mkdir(parents=True, exist_ok=True)

    for intento in range(1, max_reintentos + 1):
        faltantes = [f for f in ARCHIVOS_ESPERADOS if not (ruta_raw / f).exists()]
        if not faltantes:
            total_filas = 0
            for archivo in ARCHIVOS_ESPERADOS:
                with open(ruta_raw / archivo, "r", encoding="utf-8") as f:
                    # Restamos 1 por el encabezado
                    filas = max(sum(1 for _ in f) - 1, 0)
                    total_filas += filas
            print(f"[OK] {len(ARCHIVOS_ESPERADOS)} archivos CSV verificados en {ruta_raw} ({total_filas:,} registros).")
            return

        print(f"[Intento {intento}/{max_reintentos}] Faltan {len(faltantes)} archivos: {faltantes}")
        if intento < max_reintentos:
            time.sleep(espera_seg)

    raise FileNotFoundError(
        f"No se encontraron todos los archivos en {ruta_raw}. Faltantes: {faltantes}"
    )


if __name__ == "__main__":
    ruta_datos = Path(__file__).resolve().parent.parent / "data" / "raw"
    verificar_ingesta(ruta_datos)