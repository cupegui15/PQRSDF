import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(
    page_title="PQRSDF | Tablero Central",
    layout="wide",
    page_icon="📊"
)

# ==================================================
# CONEXIÓN GOOGLE SHEETS
# ==================================================
@st.cache_resource
def connect_gsheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = st.secrets["gcp_service_account"]

    credentials = Credentials.from_service_account_info(
        creds, scopes=scope
    )

    return gspread.authorize(credentials)

client = connect_gsheets()

SPREADSHEET_ID = "1xb56o2ao5o35QJFczVc8JpGCrPb1vEKz3fDqt4wK4ws"

sheet_pqrsdf = client.open_by_key(SPREADSHEET_ID).worksheet("PQRSDF")
sheet_festivos = client.open_by_key(SPREADSHEET_ID).worksheet("Festivos")
sheet_responsables = client.open_by_key(SPREADSHEET_ID).worksheet("Responsables")

# ==================================================
# CARGA DE DATOS
# ==================================================
@st.cache_data(ttl=300)
def load_data():
    df = pd.DataFrame(sheet_pqrsdf.get_all_records())
    festivos = pd.DataFrame(sheet_festivos.get_all_records())
    responsables = pd.DataFrame(sheet_responsables.get_all_records())
    return df, festivos, responsables

df, festivos_df, responsables_df = load_data()

# ==================================================
# LIMPIEZA Y PREPARACIÓN
# ==================================================
df['Fecha radicación'] = pd.to_datetime(df['Fecha radicación'], errors='coerce')
df['Fecha cierre'] = pd.to_datetime(df['Fecha cierre'], errors='coerce')
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')

festivos_df['Fecha'] = pd.to_datetime(festivos_df['Fecha'], errors='coerce')
festivos = festivos_df['Fecha'].dt.date.dropna().tolist()

# ==================================================
# FUNCIÓN DÍAS HÁBILES
# ==================================================
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

df['Dias_calculados'] = df.apply(
    lambda x: dias_habiles(x['Fecha radicación'], x['Fecha cierre']),
    axis=1
)

# ==================================================
# CONTROL POR USUARIO (SAML)
# ==================================================
try:
    user_email = st.experimental_user.email
except:
    user_email = None

if user_email and not responsables_df.empty:

    responsable = responsables_df[
        responsables_df['correo'] == user_email
    ]

    if not responsable.empty:
        rol = responsable['rol'].values[0]
        area_usuario = responsable['area'].values[0]

        if rol.lower() != "admin":
            df = df[df['Area principal'] == area_usuario]
    else:
        st.warning("⚠ No tienes área asignada")

# ==================================================
# FORMULARIO REGISTRO
# ==================================================
st.markdown("## 📋 Registrar nueva PQRSDF")

with st.form("form_pqrsdf"):

    categoria = st.selectbox(
        "Categoría",
        ["Petición", "Queja", "Reclamo", "Sugerencia", "Felicitación"]
    )

    area_principal = st.text_input("Área principal")
    dependencia = st.text_input("Dependencia")
    descripcion = st.text_area("Descripción")
    derecho_peticion = st.selectbox("Derecho de petición", ["Sí", "No"])

    submit = st.form_submit_button("Guardar")

if submit:

    fecha_rad = datetime.now()

    nueva_fila = [
        "",  # num caso
        fecha_rad.strftime("%Y-%m-%d"),
        "",  # fecha cierre
        fecha_rad.year,
        "",  # general
        area_principal,
        dependencia,
        descripcion,
        categoria,
        "",  # respuesta
        "Abierto",
        1,
        "",  # dias
        "No Aplica",
        fecha_rad.month,
        "I" if fecha_rad.month <= 6 else "II",
        "",  # SLA
        "", "", "", "", ""
    ]

    sheet_pqrsdf.append_row(nueva_fila, value_input_option="USER_ENTERED")

    st.success("✅ PQRSDF registrada correctamente")
    st.cache_data.clear()

st.divider()

# ==================================================
# FILTROS
# ==================================================
st.sidebar.title("🎛 Filtros")

anio = st.sidebar.multiselect("Año", sorted(df['AÑO'].dropna().unique()))
mes = st.sidebar.multiselect("Mes", sorted(df['Mes'].dropna().unique()))
semestre = st.sidebar.multiselect("Semestre", df['semestre'].dropna().unique())
area_f = st.sidebar.multiselect("Área", df['Area principal'].dropna().unique())
categoria_f = st.sidebar.multiselect("Categoría", df['Categoría'].dropna().unique())

df_f = df.copy()

if anio:
    df_f = df_f[df_f['AÑO'].isin(anio)]

if mes:
    df_f = df_f[df_f['Mes'].isin(mes)]

if semestre:
    df_f = df_f[df_f['semestre'].isin(semestre)]

if area_f:
    df_f = df_f[df_f['Area principal'].isin(area_f)]

if categoria_f:
    df_f = df_f[df_f['Categoría'].isin(categoria_f)]

# ==================================================
# CLASIFICACIÓN ESTADOS
# ==================================================
df_f['Estado'] = df_f['Estado'].astype(str).str.lower()
df_f['SLA'] = df_f['SLA'].astype(str).str.lower()

df_proceso = df_f[df_f['Estado'] != 'cerrado']
df_cerradas = df_f[df_f['Estado'] == 'cerrado']
df_vencidas = df_f[
    (df_f['SLA'].str.contains("no")) &
    (df_f['Estado'] != 'cerrado')
]

# ==================================================
# KPIs
# ==================================================
st.markdown("## 📊 Indicadores Generales")

c1, c2, c3, c4 = st.columns(4)

c1.metric("📄 Total", len(df_f))
c2.metric("⏳ En proceso", len(df_proceso))
c3.metric("❌ Vencidas", len(df_vencidas))
c4.metric("✅ Cerradas", len(df_cerradas))

st.divider()

# ==================================================
# DASHBOARD POR ÁREA
# ==================================================
st.markdown("## 📊 Comportamiento por Área")

df_area = df_f.groupby("Area principal").size().reset_index(name="Cantidad")

fig = px.bar(
    df_area,
    x="Area principal",
    y="Cantidad",
    text="Cantidad"
)

fig.update_layout(xaxis_tickangle=-40)

st.plotly_chart(fig, use_container_width=True)
st.dataframe(df_area, use_container_width=True)
