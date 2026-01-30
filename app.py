import streamlit as st
import plotly.express as px
from utils.loader import load_data_from_gsheets
from utils.metrics import kpis

st.set_page_config(
    page_title="Dashboard PQRSDF",
    layout="wide"
)

st.title("📊 Dashboard PQRSDF – Análisis y Cumplimiento")

# 🔗 IDs
SHEET_ID = "1FjApsoQIvz_nmaRCbO7NDD7N9M_noQaH"
WORKSHEET = "Base PQRSDF"  # ajusta al nombre real

# Carga datos
df = load_data_from_gsheets(SHEET_ID, WORKSHEET)

# 🎛️ Filtros
with st.sidebar:
    st.header("Filtros")
    anio = st.multiselect("Año", sorted(df['anio'].unique()))
    mes = st.multiselect("Mes", sorted(df['mes'].unique()))
    area = st.multiselect("Área", sorted(df['area'].unique()))
    tipo = st.multiselect("Tipo PQRSDF", sorted(df['tipo_pqrsdf'].unique()))

if anio:
    df = df[df['anio'].isin(anio)]
if mes:
    df = df[df['mes'].isin(mes)]
if area:
    df = df[df['area'].isin(area)]
if tipo:
    df = df[df['tipo_pqrsdf'].isin(tipo)]

# 📌 KPIs
k = kpis(df)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Total", k["total"])
c2.metric("Peticiones", k["peticiones"])
c3.metric("Quejas", k["quejas"])
c4.metric("Reclamos", k["reclamos"])
c5.metric("Vencidas", k["vencidas"])
c6.metric("Por vencer", k["por_vencer"])
c7.metric("% Cumplimiento", f"{k['cumplimiento']}%")

# 📊 Gráficas
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        px.bar(df, x="tipo_pqrsdf", title="PQRSDF por Tipo"),
        use_container_width=True
    )

with col2:
    st.plotly_chart(
        px.bar(df, y="area", orientation="h", title="PQRSDF por Área"),
        use_container_width=True
    )

st.plotly_chart(
    px.pie(df, names="estado_vencimiento", title="Estado de Vencimiento"),
    use_container_width=True
)

