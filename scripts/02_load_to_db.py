"""
Carga el CSV limpio a SQLite, normalizando el esquema.

El CSV viene en formato "wide" (una columna por tecnologia: 2G, 3G, 4G, 5G,
y otra por cada servicio). Aca se transforma a formato "long" y se separa
en tablas relacionadas:

    operadoras          4 empresas
    centros_poblados    geografia, sin repetir texto
    cobertura           operador + centro poblado + tecnologia + tiene_cobertura
    servicios           operador + centro poblado + servicio + disponible
"""

import sqlite3
import pandas as pd
from pathlib import Path

CLEAN_PATH = Path(__file__).parent.parent / "data" / "cobertura_movil_clean.csv"
DB_PATH = Path(__file__).parent.parent / "db" / "osiptel.db"

TECNOLOGIAS = ["2G", "3G", "4G", "5G"]
SERVICIOS = ["VOZ", "SMS", "MMS", "HASTA_1_MBPS", "MÁS_DE_1_MBPS"]

SCHEMA = """
DROP TABLE IF EXISTS cobertura;
DROP TABLE IF EXISTS servicios;
DROP TABLE IF EXISTS centros_poblados;
DROP TABLE IF EXISTS operadoras;

CREATE TABLE operadoras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL
);

CREATE TABLE centros_poblados (
    ubigeo_ccpp TEXT PRIMARY KEY,
    ubigeo_distrito TEXT NOT NULL,
    departamento TEXT NOT NULL,
    provincia TEXT NOT NULL,
    distrito TEXT NOT NULL,
    nombre TEXT NOT NULL,
    latitud REAL,
    longitud REAL
);

CREATE TABLE cobertura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operador_id INTEGER NOT NULL REFERENCES operadoras(id),
    ubigeo_ccpp TEXT NOT NULL REFERENCES centros_poblados(ubigeo_ccpp),
    periodo DATE NOT NULL,
    fecha_corte DATE NOT NULL,
    tecnologia TEXT NOT NULL CHECK (tecnologia IN ('2G','3G','4G','5G')),
    tiene_cobertura INTEGER NOT NULL CHECK (tiene_cobertura IN (0,1)),
    cant_estaciones_base INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operador_id INTEGER NOT NULL REFERENCES operadoras(id),
    ubigeo_ccpp TEXT NOT NULL REFERENCES centros_poblados(ubigeo_ccpp),
    periodo DATE NOT NULL,
    servicio TEXT NOT NULL,
    disponible INTEGER NOT NULL CHECK (disponible IN (0,1))
);

CREATE INDEX idx_cobertura_operador ON cobertura(operador_id);
CREATE INDEX idx_cobertura_ubigeo ON cobertura(ubigeo_ccpp);
CREATE INDEX idx_cobertura_tecnologia ON cobertura(tecnologia);
CREATE INDEX idx_centros_departamento ON centros_poblados(departamento);
"""


def main():
    df = pd.read_csv(CLEAN_PATH, dtype={"UBIGEO_CCPP": str, "UBIGEO_DISTRITO": str})
    print(f"{len(df)} filas leidas del csv limpio")

    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    # operadoras
    operadoras = sorted(df["EMPRESA_OPERADORA"].unique())
    cur.executemany("INSERT INTO operadoras (nombre) VALUES (?)", [(o,) for o in operadoras])
    conn.commit()
    operador_id = dict(cur.execute("SELECT nombre, id FROM operadoras").fetchall())

    # centros poblados, sin duplicar
    centros = (
        df[["UBIGEO_CCPP", "UBIGEO_DISTRITO", "DEPARTAMENTO", "PROVINCIA",
            "DISTRITO", "CENTRO_POBLADO", "LATITUD", "LONGITUD"]]
        .drop_duplicates(subset=["UBIGEO_CCPP"])
        .rename(columns={
            "UBIGEO_CCPP": "ubigeo_ccpp", "UBIGEO_DISTRITO": "ubigeo_distrito",
            "DEPARTAMENTO": "departamento", "PROVINCIA": "provincia",
            "DISTRITO": "distrito", "CENTRO_POBLADO": "nombre",
            "LATITUD": "latitud", "LONGITUD": "longitud",
        })
    )
    centros.to_sql("centros_poblados", conn, if_exists="append", index=False)
    conn.commit()
    print(f"{len(centros)} centros poblados unicos")

    df["operador_id"] = df["EMPRESA_OPERADORA"].map(operador_id)

    # cobertura: wide -> long, una fila por tecnologia
    partes = []
    for tech in TECNOLOGIAS:
        cant_col = f"CANT_EB_{tech}"
        sub = df[["operador_id", "UBIGEO_CCPP", "PERIODO", "FECHA_CORTE", tech, cant_col]].copy()
        sub.columns = ["operador_id", "ubigeo_ccpp", "periodo", "fecha_corte",
                       "tiene_cobertura", "cant_estaciones_base"]
        sub["tecnologia"] = tech
        partes.append(sub)

    cobertura = pd.concat(partes, ignore_index=True)
    cobertura = cobertura[["operador_id", "ubigeo_ccpp", "periodo", "fecha_corte",
                            "tecnologia", "tiene_cobertura", "cant_estaciones_base"]]
    cobertura.to_sql("cobertura", conn, if_exists="append", index=False)
    print(f"{len(cobertura)} filas en cobertura")

    # servicios: mismo criterio
    partes = []
    for serv in SERVICIOS:
        sub = df[["operador_id", "UBIGEO_CCPP", "PERIODO", serv]].copy()
        sub.columns = ["operador_id", "ubigeo_ccpp", "periodo", "disponible"]
        sub["servicio"] = serv.replace("MÁS_DE_1_MBPS", "MAS_DE_1_MBPS")
        partes.append(sub)

    servicios = pd.concat(partes, ignore_index=True)
    servicios = servicios[["operador_id", "ubigeo_ccpp", "periodo", "servicio", "disponible"]]
    servicios.to_sql("servicios", conn, if_exists="append", index=False)
    print(f"{len(servicios)} filas en servicios")

    conn.commit()

    for tabla in ["operadoras", "centros_poblados", "cobertura", "servicios"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        print(f"  {tabla}: {n} filas")

    conn.close()
    print(f"listo, base de datos en {DB_PATH}")


if __name__ == "__main__":
    main()
