import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard PQRSDF",
    layout="wide"
)

st.title("📊 Dashboard PQRSDF – Análisis y Cumplimiento")

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
# LIMPIEZA Y TRANSFORMACIÓN
# --------------------------------------------------
df['fecha_radicacion'] = pd.to_datetime(df['fecha_radicacion'], errors='coerce')
df['fecha_limite'] = pd.to_datetime(df['fecha_limite'], errors='coerce')
df['fecha_respuesta'] = pd.to_datetime(df['fecha_respuesta'], errors='coerce')

df = df.dropna(subset=['fecha_radicacion'])

df['anio'] = df['fecha_radicacion'].dt.year
df['mes'] = df['fecha_radicacion'].dt.month

df['cumple_tiempo'] = df.apply(
    lambda x: 'Cumple'
    if pd.notnull(x['fecha_respuesta'])
    and pd.notnull(x['fecha_limite'])
    and x['fecha_respuesta'] <= x['fecha_limite']
    else 'No cumple',
    axis=1
)

hoy = pd.Timestamp(datetime.now().date())

def estado_venc(row):
    if row.get('estado') == 'Cerrado':
        return 'Cerrado'
    if pd.notnull(row['fecha_limite']) and hoy > row['fecha_limite']:
        return 'Vencida'
    if pd.notnull(row['fecha_limite']) and (row['fecha_limite'] - hoy).days <= 3:
        return 'Por vencer'
    return 'En tiempo'

df['estado_vencimiento'] = df.apply(estado_venc, axis=1)

# --------------------------------------------------
# FILTROS
# --------------------------------------------------
with st.sidebar:
    st.header("🎛️ Filtros")
    anio = st.multiselect("Año", sorted(df['anio'].unique()))
    mes = st.multiselect("Mes", sorted(df['mes'].unique()))
    area = st.multiselect("Área", sorted(df['area'].dropna().unique()))
    tipo = st.multiselect("Tipo PQRSDF", sorted(df['tipo_pqrsdf'].dropna().unique()))

if anio:
    df = df[df['anio'].isin(anio)]
if mes:
    df = df[df['mes'].isin(mes)]
if area:
    df = df[df['area'].isin(area)]
if tipo:
    df = df[df['tipo_pqrsdf'].isin(tipo)]

# --------------------------------------------------
# KPIs
# --------------------------------------------------
total = len(df)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("📄 Total", total)
c2.metric("📥 Peticiones", len(df[df['tipo_pqrsdf'] == 'Petición']))
c3.metric("⚠️ Quejas", len(df[df['tipo_pqrsdf'] == 'Queja']))
c4.metric("📢 Reclamos", len(df[df['tipo_pqrsdf'] == 'Reclamo']))
c5.metric("❌ Vencidas", len(df[df['estado_vencimiento'] == 'Vencida']))
c6.metric("⏳ Por vencer", len(df[df['estado_vencimiento'] == 'Por vencer']))
c7.metric(
    "✅ % Cumplimiento",
    f"{round(len(df[df['cumple_tiempo'] == 'Cumple']) / total * 100, 1)}%"
    if total > 0 else "0%"
)

# --------------------------------------------------
# GRÁFICAS
# --------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        px.bar(df, x="tipo_pqrsdf", title="PQRSDF por Tipo", text_auto=True),
        use_container_width=True
    )

with col2:
    st.plotly_chart(
        px.bar(df, y="area", orientation="h", title="PQRSDF por Área", text_auto=True),
        use_container_width=True
    )

st.plotly_chart(
    px.pie(df, names="estado_vencimiento", title="Estado de Vencimiento"),
    use_container_width=True
)

# --------------------------------------------------
# TABLA DETALLADA
# --------------------------------------------------
st.subheader("📋 Detalle de PQRSDF")
st.dataframe(
    df.sort_values("fecha_radicacion", ascending=False),
    use_container_width=True
)
