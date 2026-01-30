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

st.title("📊 Dashboard PQRSDF – Vista General")

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
    df = pd.read_csv(CSV_URL)
    return df

df = load_data()

# --------------------------------------------------
# LIMPIEZA BÁSICA
# --------------------------------------------------
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = df['Mes'].astype(str)

df = df.dropna(subset=['AÑO', 'Mes'])

# --------------------------------------------------
# FILTROS (SOLO AÑO Y MES)
# --------------------------------------------------
with st.sidebar:
    st.header("🎛️ Filtros")
    anio = st.multiselect(
        "Año",
        sorted(df['AÑO'].dropna().unique())
    )
    mes = st.multiselect(
        "Mes",
        sorted(df['Mes'].dropna().unique())
    )

if anio:
    df = df[df['AÑO'].isin(anio)]
if mes:
    df = df[df['Mes'].isin(mes)]

# --------------------------------------------------
# KPIs BÁSICOS
# --------------------------------------------------
st.subheader("Indicadores generales")

c1, c2 = st.columns(2)
c1.metric("📄 Total PQRSDF", len(df))
c2.metric("📂 Total Categorías", df['Categoría'].nunique())

# --------------------------------------------------
# GRÁFICA SIMPLE
# --------------------------------------------------
st.subheader("PQRSDF por Categoría")

fig = px.bar(
    df,
    x='Categoría',
    title="Cantidad de PQRSDF por Categoría",
    labels={'Categoría': 'Categoría', 'count': 'Cantidad'},
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TABLA DETALLADA
# --------------------------------------------------
st.subheader("📋 Detalle de casos")

st.dataframe(
    df[
        [
            'num caso',
            'AÑO',
            'Mes',
            'Categoría',
            'Area principal',
            'Estado',
            'Descripción de la solicitud'
        ]
    ],
    use_container_width=True
)
