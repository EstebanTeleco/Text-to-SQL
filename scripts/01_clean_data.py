"""
Limpieza del CSV de cobertura movil de OSIPTEL.

El archivo original tiene tres problemas:
- viene en latin-1, no utf-8
- DEPARTAMENTO mezcla mayusculas y minusculas (Cusco / CUSCO), asi que en vez
  de 25 departamentos reales pandas cuenta 45 valores distintos
- UBIGEO_DISTRITO pierde ceros a la izquierda si se lee como numero
"""

import pandas as pd
from pathlib import Path

RAW_PATH = Path(__file__).parent.parent / "data" / "cobertura_movil.csv"
CLEAN_PATH = Path(__file__).parent.parent / "data" / "cobertura_movil_clean.csv"

TEXT_COLS = ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "CENTRO_POBLADO"]


def load_raw(path):
    return pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        dtype={"UBIGEO_CCPP": str, "UBIGEO_DISTRITO": str},
    )


def clean(df):
    df = df.copy()

    for col in TEXT_COLS:
        df[col] = df[col].str.strip().str.upper()

    df["EMPRESA_OPERADORA"] = df["EMPRESA_OPERADORA"].str.strip()

    # UBIGEO_DISTRITO tiene 6 digitos, UBIGEO_CCPP tiene 10
    df["UBIGEO_DISTRITO"] = df["UBIGEO_DISTRITO"].str.zfill(6)
    df["UBIGEO_CCPP"] = df["UBIGEO_CCPP"].str.zfill(10)

    df["PERIODO"] = pd.to_datetime(df["PERIODO"].astype(str), format="%Y%m")
    df["FECHA_CORTE"] = pd.to_datetime(df["FECHA_CORTE"].astype(str), format="%Y%m%d")

    df = df.drop(columns=["NUM"])

    # sanity check: peru esta mas o menos entre lat -19/0 y lon -82/-68
    fuera_de_rango = df[
        (df["LATITUD"] < -19) | (df["LATITUD"] > 0) |
        (df["LONGITUD"] < -82) | (df["LONGITUD"] > -68)
    ]
    if len(fuera_de_rango):
        print(f"ojo: {len(fuera_de_rango)} filas con coordenadas fuera de rango")

    return df


def main():
    df_raw = load_raw(RAW_PATH)
    print(f"leidas {len(df_raw)} filas, {len(df_raw.columns)} columnas")

    df_clean = clean(df_raw)

    print(f"departamentos: {df_clean['DEPARTAMENTO'].nunique()} (deberian ser 25)")
    print(f"operadoras: {df_clean['EMPRESA_OPERADORA'].nunique()}")
    print(f"largo ubigeo_distrito: {df_clean['UBIGEO_DISTRITO'].str.len().unique()}")
    print(f"periodo: {df_clean['PERIODO'].min()} - {df_clean['PERIODO'].max()}")

    df_clean.to_csv(CLEAN_PATH, index=False, encoding="utf-8")
    print(f"guardado en {CLEAN_PATH}")


if __name__ == "__main__":
    main()
