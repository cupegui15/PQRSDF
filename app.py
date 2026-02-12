import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from io import BytesIO

# ===============================
# CONFIGURACIÓN PRINCIPAL
# ===============================
st.set_page_config(
    page_title="PQRSDF | Universidad del Rosario",
    layout="wide",
    page_icon="📋"
)

# ===============================
# ESTILO INSTITUCIONAL
# ===============================
URL_LOGO_UR = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY0ZMIXOVuzLond_jNv713shc6TmUWej0JDQ&s"

st.markdown("""
<style>
:root { --rojo-ur:#9B0029; --gris-fondo:#f8f8f8; }
html, body, .stApp { background-color: var(--gris-fondo) !important; font-family: "Segoe UI", sans-serif; }
[data-testid="stSidebar"] { background-color: var(--rojo-ur) !important; }
[data-testid="stSidebar"] * { color:#fff !important; font-weight:600 !important; }
.banner { background-color: var(--rojo-ur); color:white; padding:1.3rem 2rem; border-radius:8px; margin-bottom:1.2rem; display:flex; justify-content:space-between; align-items:center; }
.section-title { color: var(--rojo-ur); font-weight:700; font-size:1.2rem; margin-bottom:.8rem; }
.card { background-color:white; padding:1.2rem; border-radius:10px; border:1px solid #e6e6e6; box-shadow:0 1px 3px rgba(0,0,0,.05); }
</style>
""", unsafe_allow_html=True)

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
    creds = Credentials.from_service_account_file(
        "pqrsdf-485914-1eefe7b5cc14.json",
        scopes=scope
    )
    return gspread.authorize(creds)

client = conectar()
sh = client.open_by_key(st.secrets["GOOGLE_SHEETS_ID"])
sheet_pqrs = sh.worksheet("PQRSDF")
sheet_festivos = sh.worksheet("Festivos")

# ===============================
# CARGA DATOS
# ===============================
@st.cache_data(ttl=300)
def cargar():
    df = pd.DataFrame(sheet_pqrs.get_all_records())
    festivos = pd.DataFrame(sheet_festivos.get_all_records())
    return df, festivos

df, festivos_df = cargar()

# ===============================
# FESTIVOS BLINDADOS
# ===============================
festivos = []

if not festivos_df.empty:
    festivos_df.columns = festivos_df.columns.str.strip().str.lower()
    if {'dia','mes','año'}.issubset(festivos_df.columns):

        festivos_df['dia'] = pd.to_numeric(festivos_df['dia'], errors='coerce')
        festivos_df['mes'] = pd.to_numeric(festivos_df['mes'], errors='coerce')
        festivos_df['año'] = pd.to_numeric(festivos_df['año'], errors='coerce')

        festivos_df = festivos_df.dropna(subset=['dia','mes','año'])

        if not festivos_df.empty:
            festivos_df[['dia','mes','año']] = festivos_df[['dia','mes','año']].astype(int)
            try:
                festivos = [
                    datetime(a,m,d).date()
                    for a,m,d in zip(
                        festivos_df['año'],
                        festivos_df['mes'],
                        festivos_df['dia']
                    )
                ]
            except:
                festivos = []

# ===============================
# FUNCIÓN DÍAS HÁBILES
# ===============================
def dias_habiles(inicio, fin):
    if pd.isna(inicio):
        return 0
    if pd.isna(fin):
        fin = datetime.now()
    return np.busday_count(inicio.date(), fin.date(), holidays=festivos)

# ===============================
# LIMPIEZA BASE
# ===============================
df['Fecha radicación'] = pd.to_datetime(df['Fecha radicación'], errors='coerce')
df['Fecha cierre'] = pd.to_datetime(df['Fecha cierre'], errors='coerce')
df['Dias_calculados'] = df.apply(lambda x: dias_habiles(x['Fecha radicación'], x['Fecha cierre']), axis=1)
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')

# ===============================
# MENÚ NAVEGACIÓN
# ===============================
st.sidebar.image(URL_LOGO_UR, width=140)
st.sidebar.markdown("### 🧭 Navegación")

pagina = st.sidebar.radio(
    "",
    [
        "📊 Tablero General",
        "📈 Tiempo promedio por área",
        "🏆 Ranking de cumplimiento",
        "📥 Exportación mensual"
    ]
)

# ===============================
# 📊 TABLERO GENERAL
# ===============================
if pagina == "📊 Tablero General":

    st.markdown('<div class="section-title">Indicadores Generales</div>', unsafe_allow_html=True)

    df['Estado'] = df['Estado'].astype(str).str.lower()
    df['SLA'] = df['SLA'].astype(str).str.lower()

    en_proceso = df[df['Estado'] != 'cerrado']
    cerradas = df[df['Estado'] == 'cerrado']
    vencidas = df[(df['SLA'].str.contains("no")) & (df['Estado'] != 'cerrado')]

    c1,c2,c3,c4 = st.columns(4)

    c1.markdown(f"<div class='card'><b>Total</b><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><b>En proceso</b><h2>{len(en_proceso)}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><b>Vencidas</b><h2>{len(vencidas)}</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><b>Cerradas</b><h2>{len(cerradas)}</h2></div>", unsafe_allow_html=True)

    st.divider()

    df_area = df.groupby("Area principal").size().reset_index(name="Cantidad")

    fig = px.bar(df_area, x="Area principal", y="Cantidad", text="Cantidad",
                 color="Cantidad", color_continuous_scale="Reds")
    fig.update_layout(xaxis_tickangle=-40)

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_area, use_container_width=True)

# ===============================
# 📈 TIEMPO PROMEDIO
# ===============================
elif pagina == "📈 Tiempo promedio por área":

    st.markdown('<div class="section-title">Tiempo promedio (días hábiles)</div>', unsafe_allow_html=True)

    df_cerradas = df[df['Estado'].astype(str).str.lower() == 'cerrado']

    promedio = (
        df_cerradas.groupby("Area principal")["Dias_calculados"]
        .mean()
        .reset_index()
        .sort_values("Dias_calculados", ascending=False)
    )

    promedio["Dias_calculados"] = promedio["Dias_calculados"].round(2)

    fig = px.bar(promedio, x="Area principal", y="Dias_calculados",
                 text="Dias_calculados",
                 color="Dias_calculados",
                 color_continuous_scale="Reds")

    fig.update_layout(xaxis_tickangle=-40)

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(promedio, use_container_width=True)

# ===============================
# 🏆 RANKING SLA
# ===============================
elif pagina == "🏆 Ranking de cumplimiento":

    st.markdown('<div class="section-title">Ranking de cumplimiento SLA</div>', unsafe_allow_html=True)

    df['Cumple'] = df['SLA'].astype(str).str.lower().str.contains("si")

    ranking = (
        df.groupby("Area principal")["Cumple"]
        .mean()
        .reset_index()
    )

    ranking["Cumplimiento (%)"] = (ranking["Cumple"]*100).round(2)
    ranking = ranking.sort_values("Cumplimiento (%)", ascending=False)

    fig = px.bar(ranking, x="Area principal", y="Cumplimiento (%)",
                 text="Cumplimiento (%)",
                 color="Cumplimiento (%)",
                 color_continuous_scale="RdYlGn")

    fig.update_layout(xaxis_tickangle=-40)

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ranking[["Area principal","Cumplimiento (%)"]], use_container_width=True)

# ===============================
# 📥 EXPORTACIÓN
# ===============================
elif pagina == "📥 Exportación mensual":

    st.markdown('<div class="section-title">Exportación mensual por Área</div>', unsafe_allow_html=True)

    col1,col2,col3 = st.columns(3)

    with col1:
        area_sel = st.selectbox("Área", sorted(df['Area principal'].dropna().unique()))
    with col2:
        anio_sel = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))
    with col3:
        mes_sel = st.selectbox("Mes", sorted(df['Mes'].dropna().unique()))

    df_export = df[
        (df['Area principal']==area_sel) &
        (df['AÑO']==anio_sel) &
        (df['Mes']==mes_sel)
    ]

    if df_export.empty:
        st.warning("No hay datos para exportar.")
        st.stop()

    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name="PQRSDF")

    buffer.seek(0)

    st.download_button(
        "📥 Descargar Excel",
        buffer,
        file_name=f"PQRSDF_{area_sel}_{anio_sel}_{mes_sel}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
