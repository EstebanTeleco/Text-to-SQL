# OSIPTEL Text-to-SQL

Agente que traduce preguntas en español a consultas SQL y las ejecuta contra una base de datos real de cobertura móvil en el Perú, publicada por OSIPTEL (Organismo Supervisor de Inversión Privada en Telecomunicaciones).

## Qué hace

1. Escribes una pregunta en español, por ejemplo: *"¿Qué operadora tiene más cobertura 4G?"*
2. Gemini traduce la pregunta a SQL usando el esquema de la base de datos como contexto.
3. El SQL se valida (solo se permiten consultas `SELECT`, nunca `INSERT`/`UPDATE`/`DELETE`/`DROP`).
4. Se ejecuta contra SQLite y el resultado se muestra en una interfaz web (Streamlit).

## Por qué este proyecto

Quería practicar SQL y a la vez mostrar algo de AI engineering para entrevistas, así que en vez de usar un dataset ya limpio de Kaggle elegí datos abiertos reales del Perú, con los problemas de calidad típicos de un dataset gubernamental (encoding raro, inconsistencias de texto, formato wide poco práctico para consultas).

## Fuente de datos

- Dataset: [Cobertura de servicio móvil por empresa operadora](https://www.datosabiertos.gob.pe/dataset/cobertura-de-servicio-m%C3%B3vil-por-empresa-operadora) — OSIPTEL
- Periodo: marzo 2023 (es un corte transversal, no una serie temporal)
- Licencia: Open Data Commons Attribution License
- 51,366 filas originales → 31,439 centros poblados únicos, 4 operadoras

## Problemas de calidad de datos que encontré

| Problema | Detalle | Solución |
|---|---|---|
| Encoding | El CSV viene en `latin-1`, no UTF-8 | lectura explícita con `encoding="latin-1"`, se reescribe en UTF-8 |
| Texto inconsistente | `DEPARTAMENTO` mezclaba mayúsculas y minúsculas ("Cusco" y "CUSCO"), 45 valores en vez de los 25 departamentos reales | `.str.upper().str.strip()` |
| Ceros perdidos | `UBIGEO_DISTRITO` se leía como número, perdía el formato de 6 dígitos del código INEI | se fuerza a leer como texto (`dtype=str`) + `.zfill(6)` |

## Esquema de la base de datos

El CSV original viene en formato wide (una columna por tecnología: `2G`, `3G`, `4G`, `5G`, y otra por cada servicio). Lo pasé a un esquema normalizado en formato long:

```
operadoras          4 empresas operadoras
centros_poblados     departamento, provincia, distrito, coordenadas
cobertura            operador + centro poblado + tecnología + tiene_cobertura
servicios             operador + centro poblado + servicio + disponible
```

Esto evita repetir texto miles de veces y hace que preguntas como "¿tiene cobertura 4G?" sean un filtro simple (`WHERE tecnologia = '4G'`) en vez de revisar columnas distintas por cada tecnología.

## Seguridad

El SQL lo genera un LLM y se ejecuta automáticamente, así que hay una validación previa que:
- rechaza cualquier consulta que no empiece con `SELECT`
- bloquea palabras de escritura/modificación (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `ATTACH`, `PRAGMA`)
- nunca ejecuta el SQL si no pasa esta validación

## Stack

- Python / pandas para limpieza y transformación
- SQLite como base de datos
- Gemini API (`gemini-3.5-flash`) para generar el SQL
- Streamlit para la interfaz

## Estructura

```
osiptel-text-to-sql/
├── data/
│   ├── cobertura_movil.csv           dataset original
│   └── cobertura_movil_clean.csv     dataset limpio (generado)
├── db/
│   └── osiptel.db                    sqlite (generado, no va en git)
├── scripts/
│   ├── 01_clean_data.py
│   ├── 02_load_to_db.py
│   └── 03_test_query.py
├── sql_agent.py
├── app.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Cómo correrlo

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Crea un `.env` a partir de `.env.example` con tu API key de Gemini ([Google AI Studio](https://aistudio.google.com/apikey)):

```
GEMINI_API_KEY=tu_api_key_aqui
```

Descarga el CSV de OSIPTEL desde el [portal de datos abiertos](https://www.datosabiertos.gob.pe/dataset/cobertura-de-servicio-m%C3%B3vil-por-empresa-operadora) y colócalo en `data/cobertura_movil.csv`, luego:

```bash
python scripts/01_clean_data.py
python scripts/02_load_to_db.py
streamlit run app.py
```

## Ejemplos de preguntas

- ¿Qué operadora tiene más cobertura 4G?
- ¿Cuántos centros poblados de Loreto tienen servicio de SMS?
- Compara la cantidad de centros poblados con 4G entre Claro y Entel
- Dame los 5 departamentos con más cobertura 3G
- ¿Qué operadora ofrece más internet de más de 1 Mbps en Puno?

## Posibles mejoras

- Sumar más periodos históricos para ver tendencia (ahora es un solo corte)
- Agregar el dataset de reclamos de OSIPTEL y cruzarlo por operador/geografía
- Memoria conversacional para preguntas de seguimiento ("¿y en Puno?")
- Mostrar resultados en un mapa usando las coordenadas de centros_poblados

## Fuente y licencia de los datos

Datos de OSIPTEL vía el [Portal Nacional de Datos Abiertos del Perú](https://www.datosabiertos.gob.pe), bajo licencia Open Data Commons Attribution License.
