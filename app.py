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
# CONEXIÓN GOOGLE
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
sheet = sh.worksheet("PQRSDF")

# ==================================================
# CARGA DATOS
# ==================================================
@st.cache_data(ttl=300)
def cargar():
    return pd.DataFrame(sheet.get_all_records())

df = cargar()

# ==================================================
# LIMPIEZA
# ==================================================
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')
df['Categoría'] = df['Categoría'].astype(str).str.lower().str.strip()
df['SLA'] = df['SLA'].astype(str).str.lower().str.strip()
df['Estado'] = df['Estado'].astype(str).str.lower().str.strip()
df['Fecha cierre'] = pd.to_datetime(df['Fecha cierre'], errors='coerce')

# ==================================================
# SIDEBAR
# ==================================================
st.sidebar.image(URL_LOGO_UR, width=120)
st.sidebar.markdown("### 🧭 Navegación")

pagina = st.sidebar.radio(
    "",
    [
        "🎯 Indicador por Área",
        "📌 Seguimiento",
        "📥 Exportación mensual"
    ]
)

# ==================================================
# 🎯 INDICADOR POR ÁREA
# ==================================================
if pagina == "🎯 Indicador por Área":

    st.markdown("## 🎯 Indicador de Cumplimiento por Área")

    col1, col2, col3 = st.columns(3)

    with col1:
        anio_ind = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    with col2:
        mes_ind = st.selectbox("Mes", ["Todos"] + sorted(df['Mes'].dropna().unique()))

    with col3:
        area_ind = st.selectbox("Área", ["Todas"] + sorted(df['Area principal'].dropna().unique()))

    df_ind = df[df['AÑO'] == anio_ind]

    if mes_ind != "Todos":
        df_ind = df_ind[df_ind['Mes'] == mes_ind]

    if area_ind != "Todas":
        df_ind = df_ind[df_ind['Area principal'] == area_ind]

    categorias_validas = [
        "petición",
        "queja",
        "reclamo",
        "derecho de petición"
    ]

    df_ind = df_ind[df_ind['Categoría'].isin(categorias_validas)]

    if df_ind.empty:
        st.warning("No hay registros para el periodo seleccionado.")
        st.stop()

    resumen = (
        df_ind
        .groupby('Area principal')
        .agg(
            Total=('Categoría', 'count'),
            Cumplen=('SLA', lambda x: (x.str.contains("si")).sum())
        )
        .reset_index()
    )

    resumen['Indicador (%)'] = round(
        (resumen['Cumplen'] / resumen['Total']) * 100,
        2
    )

    st.dataframe(resumen, use_container_width=True)

    fig = px.bar(
        resumen,
        x='Area principal',
        y='Indicador (%)',
        text='Indicador (%)',
        color='Indicador (%)',
        color_continuous_scale='RdYlGn',
        range_y=[0,100]
    )

    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# 📌 SEGUIMIENTO
# ==================================================
elif pagina == "📌 Seguimiento":

    st.markdown("## 📌 Seguimiento de Casos")

    col1, col2 = st.columns(2)

    with col1:
        area_seg = st.selectbox("Área", ["Todas"] + sorted(df['Area principal'].dropna().unique()))

    with col2:
        anio_seg = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    col3, col4 = st.columns(2)

    with col3:
        mes_seg = st.multiselect("Mes", sorted(df['Mes'].dropna().unique()))

    with col4:
        sla_seg = st.selectbox("SLA", ["Todos"] + sorted(df['SLA'].dropna().unique()))

    df_seg = df[df['AÑO'] == anio_seg]

    if area_seg != "Todas":
        df_seg = df_seg[df_seg['Area principal'] == area_seg]

    if mes_seg:
        df_seg = df_seg[df_seg['Mes'].isin(mes_seg)]

    if sla_seg != "Todos":
        df_seg = df_seg[df_seg['SLA'] == sla_seg]

    if df_seg.empty:
        st.warning("No hay registros con los filtros seleccionados.")
        st.stop()

    hoy = datetime.now()

    proximos = df_seg[
        (df_seg['Estado'] != "cerrado") &
        (df_seg['Fecha cierre'].notna()) &
        ((df_seg['Fecha cierre'] - hoy).dt.days <= 3) &
        ((df_seg['Fecha cierre'] - hoy).dt.days >= 0)
    ]

    total = len(df_seg)
    en_proceso = len(df_seg[df_seg['Estado'] != "cerrado"])
    cerrados = len(df_seg[df_seg['Estado'] == "cerrado"])
    no_cumplen = len(df_seg[df_seg['SLA'].str.contains("no")])
    proximos_vencer = len(proximos)

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total Casos", total)
    c2.metric("En Proceso", en_proceso)
    c3.metric("Cerrados", cerrados)
    c4.metric("No Cumplen", no_cumplen)
    c5.metric("Próximos a Vencer", proximos_vencer)

    estado_resumen = df_seg.groupby('Estado').size().reset_index(name='Cantidad')
    st.plotly_chart(px.pie(estado_resumen, names='Estado', values='Cantidad'), use_container_width=True)

    area_resumen = df_seg.groupby('Area principal').size().reset_index(name='Cantidad')
    st.plotly_chart(px.bar(area_resumen, x='Area principal', y='Cantidad', text='Cantidad'), use_container_width=True)

    tendencia = df_seg.groupby('Mes').size().reset_index(name='Cantidad').sort_values('Mes')
    st.plotly_chart(px.line(tendencia, x='Mes', y='Cantidad', markers=True), use_container_width=True)

# ==================================================
# 📥 EXPORTACIÓN
# ==================================================
elif pagina == "📥 Exportación mensual":

    st.markdown("## 📥 Descarga por Área y Año")

    col1, col2, col3 = st.columns(3)

    with col1:
        area_exp = st.selectbox("Área", sorted(df['Area principal'].dropna().unique()))

    with col2:
        anio_exp = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    with col3:
        mes_exp = st.selectbox("Mes", ["Todos"] + sorted(df['Mes'].dropna().unique()))

    df_export = df[
        (df['Area principal'] == area_exp) &
        (df['AÑO'] == anio_exp)
    ]

    meses_nombre = {
        1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",
        5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",
        9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
    }

    nombre_mes = ""

    if mes_exp != "Todos":
        df_export = df_export[df_export['Mes'] == mes_exp]
        nombre_mes = f"_{meses_nombre.get(mes_exp, mes_exp)}"

    if df_export.empty:
        st.warning("No hay registros para el periodo seleccionado.")
    else:
        area_nombre = area_exp.replace(" ", "").replace("/", "").replace("-", "")
        nombre_archivo = f"PQRSDF_{area_nombre}_{anio_exp}{nombre_mes}.xlsx"

        buffer = BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            df_export.to_excel(writer, index=False, sheet_name="PQRSDF")

        buffer.seek(0)

        st.download_button(
            "📥 Descargar archivo",
            buffer,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
