import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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
URL_BANNER_IMG = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY0ZMIXOVuzLond_jNv713shc6TmUWej0JDQ&s"

# ===============================
# CSS INSTITUCIONAL (MISMO DISEÑO)
# ===============================
st.markdown("""
<style>
:root {
    --rojo-ur: #9B0029;
    --gris-fondo: #f8f8f8;
    --texto: #222;
}
html, body, .stApp {
    background-color: var(--gris-fondo) !important;
    color: var(--texto) !important;
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
    align-items: center;
    justify-content: space-between;
}
.section-title {
    color: var(--rojo-ur);
    font-weight: 700;
    font-size: 1.2rem;
}
.card {
    background-color: #ffffff;
    padding: 1.2rem 1.4rem;
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
    <div><img src="{URL_BANNER_IMG}" width="120"></div>
</div>
""", unsafe_allow_html=True)

# ===============================
# CONEXIÓN GOOGLE SHEETS
# ===============================
@st.cache_resource
def conectar():
    creds_json = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds_dict = json.loads(creds_json)

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

client = conectar()
sh = client.open_by_key(st.secrets["GOOGLE_SHEETS_ID"])

sheet_pqrs = sh.worksheet("PQRSDF")
sheet_festivos = sh.worksheet("Festivos")
sheet_resp = sh.worksheet("Responsables")

# ===============================
# CARGA DE DATOS
# ===============================
@st.cache_data(ttl=300)
def cargar_datos():
    df = pd.DataFrame(sheet_pqrs.get_all_records())
    festivos = pd.DataFrame(sheet_festivos.get_all_records())
    resp = pd.DataFrame(sheet_resp.get_all_records())
    return df, festivos, resp

df, festivos_df, resp_df = cargar_datos()

# ===============================
# PROCESAR FESTIVOS (día/mes/año)
# ===============================
festivos_df.columns = festivos_df.columns.str.strip().str.lower()

if {'dia','mes','año'}.issubset(festivos_df.columns):
    festivos_df['fecha'] = pd.to_datetime(
        festivos_df[['año','mes','dia']],
        errors='coerce'
    )
    festivos = festivos_df['fecha'].dt.date.dropna().tolist()
else:
    festivos = []

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
# CONTROL POR USUARIO
# ===============================
try:
    user_email = st.experimental_user.email
except:
    user_email = None

resp_df.columns = resp_df.columns.str.strip().str.lower()

if user_email and not resp_df.empty:
    usuario = resp_df[resp_df['correo'] == user_email]

    if not usuario.empty:
        rol = usuario['rol'].values[0]
        area_usuario = usuario['area'].values[0]

        if rol.lower() != "admin":
            df = df[df['Area principal'] == area_usuario]

# ===============================
# SIDEBAR
# ===============================
st.sidebar.image(URL_LOGO_UR, width=150)

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

with c1:
    st.markdown(f"<div class='card'><b>Total PQRSDF</b><h2>{len(df_f)}</h2></div>", unsafe_allow_html=True)

with c2:
    st.markdown(f"<div class='card'><b>En proceso</b><h2>{len(en_proceso)}</h2></div>", unsafe_allow_html=True)

with c3:
    st.markdown(f"<div class='card'><b>Vencidas</b><h2>{len(vencidas)}</h2></div>", unsafe_allow_html=True)

with c4:
    st.markdown(f"<div class='card'><b>Cerradas</b><h2>{len(cerradas)}</h2></div>", unsafe_allow_html=True)

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
