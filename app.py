import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# ===============================
# CONFIGURACIÓN PRINCIPAL
# ===============================
st.set_page_config(
    page_title="PQRSDF | Universidad del Rosario",
    layout="wide",
    page_icon="📋"
)

# ===============================
# IMÁGENES INSTITUCIONALES
# ===============================
URL_LOGO_UR = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY0ZMIXOVuzLond_jNv713shc6TmUWej0JDQ&s"

# ===============================
# CSS INSTITUCIONAL
# ===============================
st.markdown("""
<style>
:root {
    --rojo-ur: #9B0029;
    --gris-fondo: #f8f8f8;
}
html, body, .stApp {
    background-color: var(--gris-fondo) !important;
    font-family: "Segoe UI", sans-serif;
}
[data-testid="stSidebar"] {
    background-color: var(--rojo-ur) !important;
}
[data-testid="stSidebar"] * {
    color: #fff !important;
    font-weight: 600 !important;
}
.banner {
    background-color: var(--rojo-ur);
    color: white;
    padding: 1.3rem 2rem;
    border-radius: 8px;
    margin-bottom: 1.2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.section-title {
    color: var(--rojo-ur);
    font-weight: 700;
    font-size: 1.2rem;
    margin-bottom: 0.8rem;
}
.card {
    background-color: white;
    padding: 1.2rem;
    border-radius: 10px;
    border: 1px solid #e6e6e6;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# ===============================
# BANNER
# ===============================
st.markdown(f"""
<div class="banner">
    <div>
        <h2>Tablero de Control PQRSDF</h2>
        <p>Seguimiento institucional y cumplimiento SLA</p>
    </div>
    <div><img src="{URL_LOGO_UR}" width="110"></div>
</div>
""", unsafe_allow_html=True)

# ===============================
# CONEXIÓN GOOGLE SHEETS
# ===============================
@st.cache_resource
def conectar():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = dict(st.secrets["gcp_service_account"])

    # 🔥 Arregla saltos de línea automáticamente
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scope
    )

    return gspread.authorize(creds)

client = conectar()
sh = client.open_by_key(st.secrets["GOOGLE_SHEETS_ID"])

sheet_pqrs = sh.worksheet("PQRSDF")
sheet_festivos = sh.worksheet("Festivos")

# ===============================
# CARGA DE DATOS
# ===============================
@st.cache_data(ttl=300)
def cargar_datos():
    df = pd.DataFrame(sheet_pqrs.get_all_records())
    festivos = pd.DataFrame(sheet_festivos.get_all_records())
    return df, festivos

df, festivos_df = cargar_datos()

# ===============================
# PROCESAR FESTIVOS (VERSIÓN ROBUSTA)
# ===============================
festivos_df.columns = festivos_df.columns.str.strip().str.lower()

if {'dia', 'mes', 'año'}.issubset(festivos_df.columns):

    festivos_df['dia'] = pd.to_numeric(festivos_df['dia'], errors='coerce')
    festivos_df['mes'] = pd.to_numeric(festivos_df['mes'], errors='coerce')
    festivos_df['año'] = pd.to_numeric(festivos_df['año'], errors='coerce')

    festivos_df = festivos_df.dropna(subset=['dia', 'mes', 'año'])
    festivos_df[['dia','mes','año']] = festivos_df[['dia','mes','año']].astype(int)

    festivos_df['fecha'] = festivos_df.apply(
        lambda x: datetime(x['año'], x['mes'], x['dia']),
        axis=1
    )

    festivos = festivos_df['fecha'].dt.date.tolist()

else:
    festivos = []
    st.warning("⚠ La hoja Festivos debe tener columnas: Día, Mes y Año")

# ===============================
# FUNCIÓN DÍAS HÁBILES
# ===============================
def dias_habiles(inicio, fin):
    if pd.isna(inicio):
        return 0
    if pd.isna(fin):
        fin = datetime.now()
    return np.busday_count(
        inicio.date(),
        fin.date(),
        holidays=festivos
    )

# ===============================
# LIMPIEZA BASE
# ===============================
df['Fecha radicación'] = pd.to_datetime(df['Fecha radicación'], errors='coerce')
df['Fecha cierre'] = pd.to_datetime(df['Fecha cierre'], errors='coerce')

df['Dias_calculados'] = df.apply(
    lambda x: dias_habiles(x['Fecha radicación'], x['Fecha cierre']),
    axis=1
)

df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')

# ===============================
# SIDEBAR FILTROS
# ===============================
st.sidebar.image(URL_LOGO_UR, width=140)
st.sidebar.markdown("### 🎛 Filtros")

anio_f = st.sidebar.multiselect("Año", sorted(df['AÑO'].dropna().unique()))
mes_f = st.sidebar.multiselect("Mes", sorted(df['Mes'].dropna().unique()))
area_f = st.sidebar.multiselect("Área", sorted(df['Area principal'].dropna().unique()))
categoria_f = st.sidebar.multiselect("Categoría", sorted(df['Categoría'].dropna().unique()))

df_f = df.copy()

if anio_f:
    df_f = df_f[df_f['AÑO'].isin(anio_f)]
if mes_f:
    df_f = df_f[df_f['Mes'].isin(mes_f)]
if area_f:
    df_f = df_f[df_f['Area principal'].isin(area_f)]
if categoria_f:
    df_f = df_f[df_f['Categoría'].isin(categoria_f)]

# ===============================
# CLASIFICACIÓN ESTADOS
# ===============================
df_f['Estado'] = df_f['Estado'].astype(str).str.lower()
df_f['SLA'] = df_f['SLA'].astype(str).str.lower()

en_proceso = df_f[df_f['Estado'] != 'cerrado']
cerradas = df_f[df_f['Estado'] == 'cerrado']
vencidas = df_f[
    (df_f['SLA'].str.contains("no")) &
    (df_f['Estado'] != 'cerrado')
]

# ===============================
# KPIs
# ===============================
st.markdown('<div class="section-title">📊 Indicadores Generales</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

c1.markdown(f"<div class='card'><b>Total PQRSDF</b><h2>{len(df_f)}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card'><b>En proceso</b><h2>{len(en_proceso)}</h2></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card'><b>Vencidas</b><h2>{len(vencidas)}</h2></div>", unsafe_allow_html=True)
c4.markdown(f"<div class='card'><b>Cerradas</b><h2>{len(cerradas)}</h2></div>", unsafe_allow_html=True)

st.divider()

# ===============================
# DASHBOARD POR ÁREA
# ===============================
st.markdown('<div class="section-title">📊 Comportamiento por Área</div>', unsafe_allow_html=True)

df_area = df_f.groupby("Area principal").size().reset_index(name="Cantidad")

fig = px.bar(
    df_area,
    x="Area principal",
    y="Cantidad",
    text="Cantidad",
    color="Cantidad",
    color_continuous_scale="Reds"
)

fig.update_layout(xaxis_tickangle=-40)

st.plotly_chart(fig, use_container_width=True)
st.dataframe(df_area, use_container_width=True)
