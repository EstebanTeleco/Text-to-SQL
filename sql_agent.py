"""
Agente text-to-sql. Recibe una pregunta en español, le pide a Gemini que la
traduzca a SQL, valida que sea de solo lectura, y la ejecuta contra la base
de datos de cobertura movil.
"""

import os
import re
import sqlite3
from pathlib import Path

from google import genai
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).parent / "db" / "osiptel.db"
MODEL_NAME = "gemini-3.5-flash"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

ESQUEMA = """
operadoras(id INTEGER, nombre TEXT)
  -- 'América Móvil Perú S.A.C.', 'Entel Perú S.A.', 'Telefónica del Perú S.A.A.', 'Viettel Perú S.A.C.'

centros_poblados(ubigeo_ccpp TEXT, ubigeo_distrito TEXT, departamento TEXT,
                  provincia TEXT, distrito TEXT, nombre TEXT, latitud REAL, longitud REAL)
  -- departamento va en MAYUSCULAS

cobertura(id INTEGER, operador_id INTEGER, ubigeo_ccpp TEXT, periodo DATE,
          fecha_corte DATE, tecnologia TEXT, tiene_cobertura INTEGER, cant_estaciones_base INTEGER)
  -- tecnologia: '2G' | '3G' | '4G' | '5G'
  -- tiene_cobertura: 0 o 1

servicios(id INTEGER, operador_id INTEGER, ubigeo_ccpp TEXT, periodo DATE,
          servicio TEXT, disponible INTEGER)
  -- servicio: 'VOZ' | 'SMS' | 'MMS' | 'HASTA_1_MBPS' | 'MAS_DE_1_MBPS'

relaciones:
  cobertura.operador_id -> operadoras.id
  cobertura.ubigeo_ccpp -> centros_poblados.ubigeo_ccpp
  servicios.operador_id -> operadoras.id
  servicios.ubigeo_ccpp -> centros_poblados.ubigeo_ccpp
"""

PROMPT = """Eres un experto en SQL que traduce preguntas en español a consultas SQLite validas.

{esquema}

Reglas:
- Responde unicamente con el codigo SQL, sin explicaciones ni markdown.
- Solo SELECT. Nunca INSERT, UPDATE, DELETE, DROP, ALTER.
- Usa JOIN cuando la pregunta cruce mas de una tabla.
- departamento y tecnologia se comparan en mayusculas (ej: WHERE departamento = 'LORETO').

Pregunta: {pregunta}

SQL:"""

PALABRAS_PROHIBIDAS = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
                        "CREATE", "TRUNCATE", "ATTACH", "PRAGMA"]


def generar_sql(pregunta):
    prompt = PROMPT.format(esquema=ESQUEMA, pregunta=pregunta)
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    sql = response.text.strip()
    sql = re.sub(r"^```sql\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()
    return sql


def es_sql_seguro(sql):
    limpio = sql.strip().rstrip(";").upper()
    if not limpio.startswith("SELECT"):
        return False
    return not any(p in limpio for p in PALABRAS_PROHIBIDAS)


def ejecutar_sql(sql):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql)
    columnas = [d[0] for d in cur.description]
    filas = cur.fetchall()
    conn.close()
    return columnas, filas


def responder_pregunta(pregunta):
    sql = generar_sql(pregunta)

    if not es_sql_seguro(sql):
        return {
            "sql": sql, "valido": False,
            "error": "el sql generado no es un select seguro, no se ejecuto",
            "columnas": None, "filas": None,
        }

    try:
        columnas, filas = ejecutar_sql(sql)
        return {"sql": sql, "valido": True, "error": None, "columnas": columnas, "filas": filas}
    except Exception as e:
        return {"sql": sql, "valido": False, "error": f"error al ejecutar: {e}",
                "columnas": None, "filas": None}


if __name__ == "__main__":
    pregunta = input("Pregunta: ")
    resultado = responder_pregunta(pregunta)
    print("\nSQL generado:")
    print(resultado["sql"])
    if resultado["valido"]:
        print("\nColumnas:", resultado["columnas"])
        for fila in resultado["filas"]:
            print(" ", fila)
    else:
        print("\nERROR:", resultado["error"])
