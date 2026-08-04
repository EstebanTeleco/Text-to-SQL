"""
Un par de consultas para verificar que la base de datos quedo bien armada
antes de meterle el agente de IA encima.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "osiptel.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("cobertura 4G por operadora")
q1 = """
SELECT o.nombre, COUNT(*) as centros_con_4g
FROM cobertura c
JOIN operadoras o ON c.operador_id = o.id
WHERE c.tecnologia = '4G' AND c.tiene_cobertura = 1
GROUP BY o.nombre
ORDER BY centros_con_4g DESC
"""
for row in cur.execute(q1).fetchall():
    print(" ", row)

print()
print("departamentos con menos cobertura 4G")
q2 = """
SELECT cp.departamento,
       COUNT(DISTINCT cp.ubigeo_ccpp) as total_centros,
       SUM(CASE WHEN c.tecnologia='4G' AND c.tiene_cobertura=1 THEN 1 ELSE 0 END) as con_4g
FROM centros_poblados cp
JOIN cobertura c ON cp.ubigeo_ccpp = c.ubigeo_ccpp
GROUP BY cp.departamento
ORDER BY con_4g ASC
LIMIT 5
"""
for row in cur.execute(q2).fetchall():
    print(" ", row)

conn.close()
