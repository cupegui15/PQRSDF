import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard PQRSDF",
    layout="wide"
)

st.title("📊 Dashboard PQRSDF")

# --------------------------------------------------
# URL CSV GOOGLE SHEETS
# --------------------------------------------------
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1FjApsoQIvz_nmaRCbO7NDD7N9M_noQaH/"
    "export?format=csv&gid=925681863"
)

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(CSV_URL)

df = load_data()

# --------------------------------------------------
# LIMPIEZA BÁSICA
# --------------------------------------------------
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')
df = df.dropna(subset=['AÑO', 'Mes'])

# --------------------------------------------------
# MES A TEXTO
# --------------------------------------------------
meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
df['Mes_nombre'] = df['Mes'].map(meses)
orden_meses = list(meses.values())

# --------------------------------------------------
# SIDEBAR – NAVEGACIÓN Y FILTROS
# --------------------------------------------------
with st.sidebar:

    st.header("🧭 Navegación")

    dashboard = st.radio(
        "Selecciona un dashboard",
        [
            "Dashboard por Área",
            "Dashboard En Curso",
            "Dashboard No Cumple"
        ]
    )

    st.divider()

    st.header("🎛️ Filtros globales")

    anio = st.multiselect(
        "Año",
        sorted(df['AÑO'].unique())
    )

    mes = st.multiselect(
        "Mes",
        orden_meses
    )

    categoria = st.multiselect(
        "Categoría",
        sorted(df['Categoría'].dropna().unique())
    )

# --------------------------------------------------
# APLICACIÓN DE FILTROS
# --------------------------------------------------
df_filtrado = df.copy()

if anio:
    df_filtrado = df_filtrado[df_filtrado['AÑO'].isin(anio)]

if mes:
    df_filtrado = df_filtrado[df_filtrado['Mes_nombre'].isin(mes)]

if categoria:
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categoria)]

# ==================================================
# DASHBOARD 1 – COMPORTAMIENTO POR ÁREA
# ==================================================
if dashboard == "Dashboard por Área":

    st.markdown("## 📌 Comportamiento por Área")

    df_area = (
        df_filtrado
        .groupby('Area principal', as_index=False)
        .size()
        .rename(columns={'size': 'Cantidad PQRSDF'})
        .sort_values('Cantidad PQRSDF', ascending=False)
    )

    fig = px.bar(
        df_area,
        x='Area principal',
        y='Cantidad PQRSDF',
        text='Cantidad PQRSDF',
        title="Cantidad de PQRSDF por Área"
    )

    fig.update_layout(xaxis_tickangle=-45)

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_area, use_container_width=True)

# ==================================================
# DASHBOARD 2 – EN CURSO
# ==================================================
elif dashboard == "Dashboard En Curso":

    st.markdown("## ⏳ PQRSDF en Curso")

    df_curso = df_filtrado[df_filtrado['Estado'] != 'Cerrado']

    col1, col2 = st.columns(2)

    col1.metric("Casos en curso", len(df_curso))
    col2.metric("Áreas involucradas", df_curso['Area principal'].nunique())

    fig = px.bar(
        df_curso,
        x='Area principal',
        title="PQRSDF en Curso por Área"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# DASHBOARD 3 – NO CUMPLE
# ==================================================
elif dashboard == "Dashboard No Cumple":

    st.markdown("## ❌ PQRSDF No Cumple")

    # Ajusta esta condición cuando trabajemos SLA
    df_no_cumple = df_filtrado[df_filtrado['Estado'] == 'No Cumple']

    col1, col2 = st.columns(2)

    col1.metric("Casos No Cumple", len(df_no_cumple))
    col2.metric("Áreas críticas", df_no_cumple['Area principal'].nunique())

    fig = px.bar(
        df_no_cumple,
        x='Area principal',
        title="PQRSDF No Cumple por Área"
    )

    st.plotly_chart(fig, use_container_width=True)
