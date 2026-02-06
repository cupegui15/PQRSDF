import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(
    page_title="PQRSDF | Tablero de Control",
    layout="wide",
    page_icon="📊"
)

# ==================================================
# IMÁGENES INSTITUCIONALES
# ==================================================
URL_LOGO_UR = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY0ZMIXOVuzLond_jNv713shc6TmUWej0JDQ&s"
URL_BANNER_IMG = "https://uredu-my.sharepoint.com/personal/cristian_upegui_urosario_edu_co/Documents/Imagenes/Imagen%201.jpg"

# ==================================================
# CSS INSTITUCIONAL
# ==================================================
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
    margin-bottom: .8rem;
}
.card {
    background-color: #ffffff;
    padding: 1.1rem 1.3rem;
    border-radius: 10px;
    border: 1px solid #e6e6e6;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card h4 {
    color: #9B0029;
    margin-bottom: .3rem;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# BANNER
# ==================================================
st.markdown(f"""
<div class="banner">
    <div>
        <h2>Tablero de Control PQRSDF</h2>
        <p>Análisis y seguimiento institucional</p>
    </div>
    <div><img src="{URL_BANNER_IMG}" width="130" style="border-radius:6px;"></div>
</div>
""", unsafe_allow_html=True)

# ==================================================
# CONEXIÓN A GOOGLE SHEETS
# ==================================================
@st.cache_resource
def connect_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = st.secrets["gcp_service_account"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
    return gspread.authorize(credentials)

client = connect_gsheets()

sheet = client.open_by_key(
    "1xb56o2ao5o35QJFczVc8JpGCrPb1vEKz3fDqt4wK4ws"
).worksheet("PQRSDF")

# ==================================================
# FORMULARIO PQRSDF
# ==================================================
st.markdown('<div class="section-title">📋 Registro de PQRSDF</div>', unsafe_allow_html=True)

with st.form("form_pqrsdf"):
    categoria = st.selectbox(
        "Categoría",
        ["Petición", "Queja", "Reclamo", "Sugerencia", "Felicitación"]
    )
    area_principal = st.text_input("Área principal")
    dependencia = st.text_input("Dependencia")
    descripcion = st.text_area("Descripción de la solicitud")
    estado = st.selectbox("Estado", ["Abierto", "Cerrado"])
    derecho_peticion = st.selectbox("Derecho de petición", ["Sí", "No"])

    submit = st.form_submit_button("Guardar PQRSDF")

if submit:
    nueva_fila = [
        "",  # num caso
        datetime.now().strftime("%Y-%m-%d"),
        "",  # fecha cierre
        datetime.now().year,
        "",  # general
        area_principal,
        dependencia,
        descripcion,
        categoria,
        "",  # respuesta
        estado,
        1,
        "",  # días
        "No Aplica",
        derecho_peticion,
        datetime.now().month,
        "I",
        "", "", "", "", ""
    ]

    sheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
    st.success("✅ PQRSDF registrada correctamente")
    st.cache_data.clear()

st.markdown("---")

# ==================================================
# CARGA DE DATOS (LECTURA)
# ==================================================
@st.cache_data(ttl=300)
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# ==================================================
# PREPARACIÓN DE DATOS
# ==================================================
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')
df = df.dropna(subset=['AÑO', 'Mes'])

meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

df['Mes_nombre'] = df['Mes'].map(meses)
df['Semestre'] = df['Mes'].apply(lambda x: "Semestre 1" if x <= 6 else "Semestre 2")

# ==================================================
# SIDEBAR
# ==================================================
st.sidebar.image(URL_LOGO_UR, width=140)

st.sidebar.markdown("### 🧭 Navegación")

dashboard = st.sidebar.radio(
    "",
    ["📊 Comportamiento por Área", "⏳ En Curso", "❌ No Cumple (SLA)"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Filtros")

anio = st.sidebar.multiselect("Año", sorted(df['AÑO'].unique()))
semestre = st.sidebar.multiselect("Semestre", ["Semestre 1", "Semestre 2"])
mes = st.sidebar.multiselect("Mes", list(meses.values()))
categoria_f = st.sidebar.multiselect(
    "Categoría",
    sorted(df['Categoría'].dropna().unique())
)

# ==================================================
# FILTROS
# ==================================================
df_f = df.copy()

if anio:
    df_f = df_f[df_f['AÑO'].isin(anio)]
if semestre:
    df_f = df_f[df_f['Semestre'].isin(semestre)]
if mes:
    df_f = df_f[df_f['Mes_nombre'].isin(mes)]
if categoria_f:
    df_f = df_f[df_f['Categoría'].isin(categoria_f)]

# ==================================================
# KPI SLA
# ==================================================
df_no_cumple = df_f[
    df_f['SLA'].astype(str).str.lower().str.contains("no")
]

# ==================================================
# KPIs
# ==================================================
st.markdown('<div class="section-title">Indicadores generales</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"<div class='card'><h4>📄 Total PQRSDF</h4><h2>{len(df_f)}</h2></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='card'><h4>🏢 Áreas</h4><h2>{df_f['Area principal'].nunique()}</h2></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='card'><h4>🗂️ Categorías</h4><h2>{df_f['Categoría'].nunique()}</h2></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='card'><h4>🗓️ Periodos</h4><h2>{df_f[['AÑO','Mes_nombre']].drop_duplicates().shape[0]}</h2></div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='card'><h4>❌ No Cumple SLA</h4><h2>{len(df_no_cumple)}</h2></div>", unsafe_allow_html=True)

st.markdown("---")

# ==================================================
# DASHBOARDS
# ==================================================
if dashboard == "📊 Comportamiento por Área":

    df_area = df_f.groupby("Area principal").size().reset_index(name="Cantidad")

    fig = px.bar(df_area, x="Area principal", y="Cantidad", text="Cantidad")
    fig.update_layout(xaxis_tickangle=-40)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_area, use_container_width=True)

elif dashboard == "⏳ En Curso":

    df_curso = df_f[df_f['Estado'].str.lower() != 'cerrado']
    df_area = df_curso.groupby("Area principal").size().reset_index(name="En curso")

    fig = px.bar(df_area, x="Area principal", y="En curso", text="En curso")
    fig.update_layout(xaxis_tickangle=-40)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_area, use_container_width=True)
