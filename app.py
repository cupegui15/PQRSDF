import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from io import BytesIO

# ==================================================
# CONFIGURACIÓN
# ==================================================
st.set_page_config(
    page_title="PQRSDF | Universidad del Rosario",
    layout="wide",
    page_icon="📋"
)

URL_LOGO_UR = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY0ZMIXOVuzLond_jNv713shc6TmUWej0JDQ&s"

# ==================================================
# ESTILO
# ==================================================
st.markdown("""
<style>
:root { --rojo:#9B0029; --gris:#f8f8f8; }
html, body, .stApp { background-color:var(--gris)!important; font-family:"Segoe UI",sans-serif;}
[data-testid="stSidebar"] { background-color:var(--rojo)!important; }
[data-testid="stSidebar"] * { color:#fff!important; font-weight:600!important; }
.banner { background-color:var(--rojo); color:white; padding:1.2rem; border-radius:8px; margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center;}
.section-title { color:var(--rojo); font-weight:700; font-size:1.2rem; margin-bottom:.8rem;}
.card { background:white; padding:1.2rem; border-radius:10px; border:1px solid #e6e6e6;}
</style>
""", unsafe_allow_html=True)

# Reducir tamaño visual de filtros
st.markdown("""
<style>
[data-testid="stSidebar"] .stMultiSelect div {
    font-size: 13px;
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
        <p>Seguimiento institucional y cumplimiento SLA</p>
    </div>
    <div><img src="{URL_LOGO_UR}" width="100"></div>
</div>
""", unsafe_allow_html=True)

# ==================================================
# CONEXIÓN GOOGLE SHEETS
# ==================================================
@st.cache_resource
def conectar():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(
        "pqrsdf-485914-1eefe7b5cc14.json",
        scopes=scope
    )
    return gspread.authorize(creds)

client = conectar()
sh = client.open_by_key(st.secrets["GOOGLE_SHEETS_ID"])
sheet_pqrs = sh.worksheet("PQRSDF")
sheet_festivos = sh.worksheet("Festivos")

# ==================================================
# CARGA DATOS
# ==================================================
@st.cache_data(ttl=300)
def cargar():
    df = pd.DataFrame(sheet_pqrs.get_all_records())
    festivos = pd.DataFrame(sheet_festivos.get_all_records())
    return df, festivos

df, festivos_df = cargar()

# ==================================================
# FESTIVOS
# ==================================================
festivos = []

if not festivos_df.empty:
    festivos_df.columns = festivos_df.columns.str.strip().str.lower()
    if {'dia','mes','año'}.issubset(festivos_df.columns):
        festivos_df[['dia','mes','año']] = festivos_df[['dia','mes','año']].apply(pd.to_numeric, errors='coerce')
        festivos_df = festivos_df.dropna()
        festivos = [
            datetime(int(a),int(m),int(d)).date()
            for a,m,d in zip(festivos_df['año'],festivos_df['mes'],festivos_df['dia'])
        ]

# ==================================================
# DÍAS HÁBILES
# ==================================================
def dias_habiles(inicio, fin):
    if pd.isna(inicio):
        return 0
    if pd.isna(fin):
        fin = datetime.now()
    return np.busday_count(inicio.date(), fin.date(), holidays=festivos)

df['Fecha radicación'] = pd.to_datetime(df['Fecha radicación'], errors='coerce')
df['Fecha cierre'] = pd.to_datetime(df['Fecha cierre'], errors='coerce')
df['Dias_calculados'] = df.apply(lambda x: dias_habiles(x['Fecha radicación'], x['Fecha cierre']), axis=1)

df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')
df['Semestre'] = df['Mes'].apply(lambda x: "Semestre 1" if x <= 6 else "Semestre 2")

df['Estado'] = df['Estado'].astype(str).str.lower()
df['SLA'] = df['SLA'].astype(str).str.lower()

# ==================================================
# SIDEBAR
# ==================================================
st.sidebar.image(URL_LOGO_UR, width=120)
st.sidebar.markdown("### 🧭 Navegación")

pagina = st.sidebar.radio(
    "",
    [
        "📊 Tablero General",
        "📈 Tiempo promedio por área",
        "🏆 Ranking de cumplimiento",
        "📊 Comparativos",
        "🎯 Indicador por Área",
        "📥 Exportación mensual"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛 Filtros")

col1, col2 = st.sidebar.columns(2)
with col1:
    anio_f = st.multiselect("Año", sorted(df['AÑO'].dropna().unique()))
with col2:
    semestre_f = st.multiselect("Semestre", sorted(df['Semestre'].dropna().unique()))

col3, col4 = st.sidebar.columns(2)
with col3:
    mes_f = st.multiselect("Mes", sorted(df['Mes'].dropna().unique()))
with col4:
    sla_f = st.multiselect("SLA", sorted(df['SLA'].dropna().unique()))

area_f = st.sidebar.multiselect("Área", sorted(df['Area principal'].dropna().unique()))
categoria_f = st.sidebar.multiselect("Categoría", sorted(df['Categoría'].dropna().unique()))

# ==================================================
# APLICAR FILTROS
# ==================================================
df_filtrado = df.copy()

if anio_f:
    df_filtrado = df_filtrado[df_filtrado['AÑO'].isin(anio_f)]
if semestre_f:
    df_filtrado = df_filtrado[df_filtrado['Semestre'].isin(semestre_f)]
if mes_f:
    df_filtrado = df_filtrado[df_filtrado['Mes'].isin(mes_f)]
if area_f:
    df_filtrado = df_filtrado[df_filtrado['Area principal'].isin(area_f)]
if categoria_f:
    df_filtrado = df_filtrado[df_filtrado['Categoría'].isin(categoria_f)]
if sla_f:
    df_filtrado = df_filtrado[df_filtrado['SLA'].isin(sla_f)]

# ==================================================
# DASHBOARDS
# ==================================================
if pagina == "📊 Tablero General":

    en_proceso = df_filtrado[df_filtrado['Estado'] != 'cerrado']
    cerradas = df_filtrado[df_filtrado['Estado'] == 'cerrado']
    vencidas = df_filtrado[(df_filtrado['SLA'].str.contains("no")) & (df_filtrado['Estado'] != 'cerrado')]

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Total", len(df_filtrado))
    c2.metric("En proceso", len(en_proceso))
    c3.metric("Vencidas", len(vencidas))
    c4.metric("Cerradas", len(cerradas))

    df_area = df_filtrado.groupby("Area principal").size().reset_index(name="Cantidad")
    fig = px.bar(df_area, x="Area principal", y="Cantidad", text="Cantidad", color="Cantidad")
    st.plotly_chart(fig, use_container_width=True)

elif pagina == "📈 Tiempo promedio por área":

    df_cerradas = df_filtrado[df_filtrado['Estado'] == 'cerrado']

    promedio = (
        df_cerradas.groupby("Area principal")["Dias_calculados"]
        .mean().reset_index()
    )

    promedio["Dias_calculados"] = promedio["Dias_calculados"].round(2)

    fig = px.bar(promedio, x="Area principal", y="Dias_calculados",
                 text="Dias_calculados", color="Dias_calculados")
    st.plotly_chart(fig, use_container_width=True)

elif pagina == "🏆 Ranking de cumplimiento":

    ranking = (
        df_filtrado.assign(Cumple=lambda x: x['SLA'].str.contains("si"))
        .groupby("Area principal")["Cumple"]
        .mean().reset_index()
    )

    ranking["Cumplimiento (%)"] = (ranking["Cumple"]*100).round(2)

    fig = px.bar(ranking, x="Area principal", y="Cumplimiento (%)",
                 text="Cumplimiento (%)", color="Cumplimiento (%)",
                 color_continuous_scale="RdYlGn")
    st.plotly_chart(fig, use_container_width=True)

elif pagina == "📊 Comparativos":

    comparativo = (
        df_filtrado.groupby(["AÑO","Mes","Area principal"])
        .size().reset_index(name="Cantidad")
    )

    fig = px.line(comparativo, x="Mes", y="Cantidad",
                  color="Area principal", markers=True)
    st.plotly_chart(fig, use_container_width=True)

elif pagina == "🎯 Indicador por Área":

    categorias_validas = ["Petición", "Queja", "Reclamo"]

    df_ind = df_filtrado[
        (df_filtrado["Categoría"].isin(categorias_validas)) |
        (df_filtrado["Derecho de petición"].astype(str).str.lower() == "sí")
    ]

    df_ind["Cumple"] = df_ind["SLA"].str.contains("si")

    indicador = (
        df_ind.groupby("Area principal")
        .agg(Total=("Cumple","count"),
             Cumplen=("Cumple","sum"))
        .reset_index()
    )

    indicador["Indicador (%)"] = (indicador["Cumplen"]/indicador["Total"]*100).round(2)

    fig = px.bar(indicador, x="Area principal", y="Indicador (%)",
                 text="Indicador (%)", color="Indicador (%)",
                 color_continuous_scale="RdYlGn")
    st.plotly_chart(fig, use_container_width=True)

elif pagina == "📥 Exportación mensual":

    if df_filtrado.empty:
        st.warning("No hay datos con los filtros aplicados.")
    else:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name="PQRSDF")
        buffer.seek(0)

        st.download_button(
            "📥 Descargar Excel filtrado",
            buffer,
            file_name="PQRSDF_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
