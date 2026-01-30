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
# LIMPIEZA Y NORMALIZACIÓN
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
# SIDEBAR – FILTROS
# --------------------------------------------------
with st.sidebar:
    st.header("🎛️ Filtros")

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

if anio:
    df = df[df['AÑO'].isin(anio)]

if mes:
    df = df[df['Mes_nombre'].isin(mes)]

if categoria:
    df = df[df['Categoría'].isin(categoria)]

# --------------------------------------------------
# DASHBOARD: COMPORTAMIENTO POR ÁREA
# --------------------------------------------------
st.markdown("## 📌 Comportamiento por Área")

st.markdown(
    """
    Visualiza la **cantidad de PQRSDF por área** en el periodo seleccionado,
    permitiendo identificar **concentración de solicitudes, quejas o peticiones**
    por dependencia.
    """
)

# Agrupación por área
df_area = (
    df
    .groupby('Area principal', as_index=False)
    .size()
    .rename(columns={'size': 'Cantidad PQRSDF'})
    .sort_values('Cantidad PQRSDF', ascending=False)
)

# --------------------------------------------------
# GRÁFICO DE BARRAS – TOP POR ÁREA
# --------------------------------------------------
fig = px.bar(
    df_area,
    x='Area principal',
    y='Cantidad PQRSDF',
    title="Cantidad de PQRSDF por Área",
    text='Cantidad PQRSDF'
)

fig.update_layout(
    xaxis_title="Área",
    yaxis_title="Cantidad de PQRSDF",
    xaxis_tickangle=-45
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TABLA DE APOYO
# --------------------------------------------------
st.subheader("📋 Detalle por Área")

st.dataframe(
    df_area,
    use_container_width=True
)
