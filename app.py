import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
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
# PARÁMETROS GOOGLE SHEETS
# --------------------------------------------------
SHEET_ID = "1FjApsoQIvz_nmaRCbO7NDD7N9M_noQaH"
WORKSHEET_GID = 925681863  # <-- GID tomado de la URL

# --------------------------------------------------
# CARGA DE DATOS DESDE GOOGLE SHEETS
# --------------------------------------------------
@st.cache_data(ttl=300)
def load_data_from_gsheets(sheet_id, worksheet_gid):

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

    client = gspread.authorize(credentials)

    try:
        sheet = client.open_by_key(sheet_id)
    except Exception:
        st.error("❌ No se pudo abrir el Google Sheet. Verifica que esté compartido con la service account.")
        st.stop()

    try:
        worksheet = sheet.get_worksheet_by_id(worksheet_gid)
    except Exception:
        st.error("❌ No se pudo acceder a la pestaña indicada por GID.")
        st.stop()

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        st.warning("⚠️ La hoja está vacía o no tiene encabezados.")
        st.stop()

    # ------------------------
    # LIMPIEZA Y TRANSFORMACIÓN
    # ------------------------
    df['fecha_radicacion'] = pd.to_datetime(df['fecha_radicacion'], errors='coerce')
    df['fecha_limite'] = pd.to_datetime(df['fecha_limite'], errors='coerce')
    df['fecha_respuesta'] = pd.to_datetime(df['fecha_respuesta'], errors='coerce')

    df = df.dropna(subset=['fecha_radicacion'])

    df['anio'] = df['fecha_radicacion'].dt.year
    df['mes'] = df['fecha_radicacion'].dt.month

    # Cumplimiento de tiempos
    df['cumple_tiempo'] = df.apply(
        lambda x: 'Cumple'
        if pd.notnull(x['fecha_respuesta']) and pd.notnull(x['fecha_limite'])
        and x['fecha_respuesta'] <= x['fecha_limite']
        else 'No cumple',
        axis=1
    )

    # Estado de vencimiento
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

    return df


# --------------------------------------------------
# KPIs
# --------------------------------------------------
def calcular_kpis(df):
    total = len(df)

    return {
        "total": total,
        "peticiones": len(df[df['tipo_pqrsdf'] == 'Petición']),
        "quejas": len(df[df['tipo_pqrsdf'] == 'Queja']),
        "reclamos": len(df[df['tipo_pqrsdf'] == 'Reclamo']),
        "vencidas": len(df[df['estado_vencimiento'] == 'Vencida']),
        "por_vencer": len(df[df['estado_vencimiento'] == 'Por vencer']),
        "cumplimiento": round(
            len(df[df['cumple_tiempo'] == 'Cumple']) / total * 100, 1
        ) if total > 0 else 0
    }


# --------------------------------------------------
# EJECUCIÓN PRINCIPAL
# --------------------------------------------------
df = load_data_from_gsheets(SHEET_ID, WORKSHEET_GID)

# --------------------------------------------------
# FILTROS
# --------------------------------------------------
with st.sidebar:
    st.header("🎛️ Filtros")
    anio = st.multiselect("Año", sorted(df['anio'].dropna().unique()))
    mes = st.multiselect("Mes", sorted(df['mes'].dropna().unique()))
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
# KPIs VISUALES
# --------------------------------------------------
k = calcular_kpis(df)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("📄 Total", k["total"])
c2.metric("📥 Peticiones", k["peticiones"])
c3.metric("⚠️ Quejas", k["quejas"])
c4.metric("📢 Reclamos", k["reclamos"])
c5.metric("❌ Vencidas", k["vencidas"])
c6.metric("⏳ Por vencer", k["por_vencer"])
c7.metric("✅ % Cumplimiento", f"{k['cumplimiento']}%")

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
# TA
