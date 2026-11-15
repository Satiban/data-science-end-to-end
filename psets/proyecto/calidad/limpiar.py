from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

TABLAS = [
    "patients",
    "dentists",
    "insurers",
    "appointments",
    "missed_appointments",
    "invoices",
    "procedures",
    "treatment_lines",
    "treatment_plans",
    "treatment_sessions",
    "patient_followups",
]


def cargar_crudo(nombre: str) -> pd.DataFrame:
    df = pd.read_csv(
        RAW_DIR / f"{nombre}.csv",
        dtype="string",
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    # Eliminar espacios laterales y convertir cadenas vacías en NA estándar
    df = df.apply(lambda col: col.str.strip().replace("", pd.NA))
    # Deduplicar por identificador primario si existiera
    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"], keep="first")
    return df


def limpiar_tabla(nombre: str, df: pd.DataFrame, planes_inicio: dict | None = None) -> pd.DataFrame:
    df = df.copy()

    # Normalizar campos categóricos a minúsculas
    for col in ["status", "visit_type", "outcome", "contact_method", "contact_result", "contract", "scheme", "list_name"]:
        if col in df.columns:
            df[col] = df[col].str.lower()

    # Normalizar número de factura en mayúsculas
    if "invoice_no" in df.columns:
        df["invoice_no"] = df["invoice_no"].str.upper()

    # Validar rango [0, 1] en cover_fraction (manteniendo NA en pacientes sin seguro)
    if "cover_fraction" in df.columns:
        cov = pd.to_numeric(df["cover_fraction"], errors="coerce")
        df["cover_fraction"] = cov.where((cov >= 0) & (cov <= 1), pd.NA)

    # Marcar anomalía temporal en sesiones previas al inicio del plan (conservando el registro)
    if nombre == "treatment_sessions" and planes_inicio is not None:
        planned_dt = pd.to_datetime(df["planned_date"], format="%Y-%m-%d", errors="coerce")
        completed_dt = pd.to_datetime(df["completed_at"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        start_dt = pd.to_datetime(df["treatment_plan_id"].map(planes_inicio), errors="coerce")
        df["flag_fecha_anterior_inicio"] = (
            (planned_dt.notna() & start_dt.notna() & (planned_dt < start_dt))
            | (completed_dt.notna() & start_dt.notna() & (completed_dt.dt.normalize() < start_dt))
        )

    return df


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Cargar fechas de inicio de planes para validar sesiones
    planes_raw = cargar_crudo("treatment_plans")
    planes_inicio = dict(zip(planes_raw["id"], planes_raw["start_date"]))

    total_filas = 0
    print("=" * 75)
    print("ORALSOLUTIONS - LIMPIEZA DE DATOS (RAW -> PROCESSED)")
    print("=" * 75)

    for tabla in TABLAS:
        df_raw = cargar_crudo(tabla)
        df_clean = limpiar_tabla(tabla, df_raw, planes_inicio=planes_inicio)
        salida = PROCESSED_DIR / f"{tabla}.csv"
        df_clean.to_csv(salida, index=False, encoding="utf-8")
        total_filas += len(df_clean)
        print(f"[OK] {tabla:22} -> {len(df_clean):6,} filas guardadas en {salida.name}")

    print("-" * 75)
    print(f"Total registros limpios en data/processed/: {total_filas:,}")


if __name__ == "__main__":
    main()