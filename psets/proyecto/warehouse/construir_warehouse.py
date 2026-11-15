from pathlib import Path
import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = Path(__file__).resolve().parent / "oralsolutions.duckdb"

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


def main() -> None:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(
            f"No existe {PROCESSED_DIR}. Ejecuta primero: python calidad/limpiar.py"
        )

    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    print("=" * 75)
    print(f"ORALSOLUTIONS - CONSTRUCCIÓN DE WAREHOUSE LOCAL ({DB_PATH.name})")
    print("=" * 75)

    total_csv = 0
    total_db = 0

    for tabla in TABLAS:
        ruta_csv = PROCESSED_DIR / f"{tabla}.csv"
        if not ruta_csv.exists():
            raise FileNotFoundError(f"Falta archivo limpio: {ruta_csv}")

        df = pd.read_csv(ruta_csv, dtype="string", keep_default_na=False)
        filas_csv = len(df)

        con.execute(
            f"""
            CREATE OR REPLACE TABLE raw.{tabla} AS
            SELECT * FROM read_csv_auto('{ruta_csv.as_posix()}', all_varchar=true);
            """
        )

        filas_db = con.execute(f"SELECT COUNT(*) FROM raw.{tabla};").fetchone()[0]
        assert filas_csv == filas_db, (
            f"Descuadre en {tabla}: CSV={filas_csv} vs DuckDB={filas_db}"
        )

        total_csv += filas_csv
        total_db += filas_db
        print(f"[OK] raw.{tabla:22} | CSV: {filas_csv:6,} | DuckDB: {filas_db:6,}")

    con.close()
    print("-" * 75)
    print(f"Verificación total: CSV = {total_csv:,} filas | DuckDB = {total_db:,} filas")


if __name__ == "__main__":
    main()