import streamlit as st
import pandas as pd

from sql_agent import responder_pregunta

st.set_page_config(page_title="OSIPTEL Text-to-SQL", page_icon="📡", layout="centered")

st.title("📡 OSIPTEL Text-to-SQL")
st.caption(
    "Pregunta en español sobre cobertura móvil en Perú. El agente traduce tu "
    "pregunta a SQL, la ejecuta contra una base de datos real de OSIPTEL "
    "(marzo 2023) y te muestra el resultado."
)

with st.expander("Ejemplos de preguntas"):
    st.markdown("""
    - ¿Qué operadora tiene más cobertura 4G?
    - ¿Cuántos centros poblados de Loreto tienen servicio de SMS?
    - ¿Qué departamento tiene más estaciones base de 5G?
    - Compara la cobertura 3G entre Claro y Entel
    - Dame los 5 departamentos con más cobertura 3G
    """)

pregunta = st.text_input("Tu pregunta:", placeholder="Ej: ¿Qué operadora tiene más cobertura 4G?")

if st.button("Consultar", type="primary") and pregunta:
    with st.spinner("Generando SQL y consultando la base de datos..."):
        resultado = responder_pregunta(pregunta)

    st.subheader("SQL generado")
    st.code(resultado["sql"], language="sql")

    if resultado["valido"]:
        st.subheader("Resultado")
        if resultado["filas"]:
            df = pd.DataFrame(resultado["filas"], columns=resultado["columnas"])
            st.dataframe(df, use_container_width=True)
            st.caption(f"{len(df)} fila(s)")
        else:
            st.info("La consulta no devolvió resultados.")
    else:
        st.error(resultado["error"])

st.divider()
st.caption(
    "Fuente: OSIPTEL — Cobertura de servicio móvil por empresa operadora "
    "(datosabiertos.gob.pe). Licencia Open Data Commons Attribution License."
)
