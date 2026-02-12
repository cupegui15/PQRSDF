import streamlit as st
import pandas as pd
import plotly.express as px
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
# DICCIONARIO MESES
# ==================================================
meses_nombre = {
    1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",
    5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",
    9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
}
meses_invertido = {v:k for k,v in meses_nombre.items()}

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

st.markdown(f"""
<div class="banner">
    <div>
        <h2>Tablero de Control PQRSDF</h2>       
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

@st.cache_data(ttl=300)
def cargar():
    return pd.DataFrame(sheet.get_all_records())

df = cargar()

# ==================================================
# LIMPIEZA
# ==================================================
df.columns = df.columns.str.strip()
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

pagina = st.sidebar.radio(
    "",
    [
        "📌 Seguimiento Diario",
        "🎯 Indicador por Área",
        "🔎 Búsqueda de Caso",
        "📥 Exportación mensual"
    ]
)

# ==================================================
# 📌 SEGUIMIENTO DIARIO
# ==================================================
if pagina == "📌 Seguimiento Diario":

    st.markdown("## 📌 Seguimiento de Casos")

    col1, col2 = st.columns(2)

    with col1:
        area_seg = st.selectbox("Área", ["Todas"] + sorted(df['Area principal'].dropna().unique()))

    with col2:
        anio_seg = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    meses_disponibles = sorted(df['Mes'].dropna().unique())
    meses_visual = [meses_nombre[m] for m in meses_disponibles if m in meses_nombre]

    mes_seg = st.multiselect("Mes", meses_visual)

    sla_seg = st.selectbox("SLA", ["Todos"] + sorted(df['SLA'].dropna().unique()))

    df_seg = df[df['AÑO'] == anio_seg]

    if area_seg != "Todas":
        df_seg = df_seg[df_seg['Area principal'] == area_seg]

    if mes_seg:
        meses_numericos = [meses_invertido[m] for m in mes_seg]
        df_seg = df_seg[df_seg['Mes'].isin(meses_numericos)]

    if sla_seg != "Todos":
        df_seg = df_seg[df_seg['SLA'] == sla_seg]

    if df_seg.empty:
        st.warning("No hay registros con los filtros seleccionados.")
        st.stop()

    # 🔥 Cálculo seguro de días restantes
    hoy = pd.Timestamp.today()

    df_seg['Fecha cierre'] = pd.to_datetime(df_seg['Fecha cierre'], errors='coerce')
    df_seg['Dias_restantes'] = (df_seg['Fecha cierre'] - hoy).dt.days

    proximos = df_seg[
        (df_seg['Estado'] != "cerrado") &
        (df_seg['Dias_restantes'].notna()) &
        (df_seg['Dias_restantes'] <= 3) &
        (df_seg['Dias_restantes'] >= 0)
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

    st.divider()

    if not proximos.empty:
        st.markdown("### ⚠️ Casos Próximos a Vencer")
        st.dataframe(
            proximos[['num caso','Area principal','Categoría','Fecha cierre','Dias_restantes','SLA','Estado']]
            .sort_values('Dias_restantes'),
            use_container_width=True
        )

# ==================================================
# 🔎 BÚSQUEDA
# ==================================================
elif pagina == "🔎 Búsqueda de Caso":

    st.markdown("## 🔎 Búsqueda de Caso")

    numero = st.text_input("Ingrese número de caso")

    if numero:
        resultado = df[df['num caso'].astype(str) == numero.strip()]
        if resultado.empty:
            st.warning("No se encontró ningún caso.")
        else:
            st.success("Caso encontrado")
            st.dataframe(resultado, use_container_width=True)

# ==================================================
# 🎯 INDICADOR
# ==================================================
elif pagina == "🎯 Indicador por Área":

    st.markdown("## 🎯 Indicador de Cumplimiento por Área")

    anio_ind = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    meses_disponibles = sorted(df['Mes'].dropna().unique())
    meses_visual = [meses_nombre[m] for m in meses_disponibles if m in meses_nombre]

    mes_ind = st.multiselect("Mes", meses_visual)

    df_ind = df[df['AÑO'] == anio_ind]

    if mes_ind:
        meses_numericos = [meses_invertido[m] for m in mes_ind]
        df_ind = df_ind[df_ind['Mes'].isin(meses_numericos)]

    categorias_validas = ["petición","queja","reclamo","derecho de petición"]

    df_ind = df_ind[df_ind['Categoría'].isin(categorias_validas)]

    if df_ind.empty:
        st.warning("No hay registros.")
        st.stop()

    resumen = (
        df_ind.groupby('Area principal')
        .agg(
            Total=('Categoría','count'),
            Cumplen=('SLA',lambda x:(x.str.contains("si")).sum())
        )
        .reset_index()
    )

    resumen['Indicador (%)'] = round((resumen['Cumplen']/resumen['Total'])*100,2)

    st.dataframe(resumen, use_container_width=True)
    st.plotly_chart(px.bar(resumen,x='Area principal',y='Indicador (%)',text='Indicador (%)'),use_container_width=True)

# ==================================================
# 📥 EXPORTACIÓN
# ==================================================
elif pagina == "📥 Exportación mensual":

    st.markdown("## 📥 Descarga por Área y Año")

    area_exp = st.selectbox("Área", sorted(df['Area principal'].dropna().unique()))
    anio_exp = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))
    mes_exp = st.selectbox("Mes", ["Todos"] + [meses_nombre[m] for m in sorted(df['Mes'].dropna().unique())])

    df_export = df[(df['Area principal']==area_exp)&(df['AÑO']==anio_exp)]

    nombre_mes=""

    if mes_exp!="Todos":
        df_export=df_export[df_export['Mes']==meses_invertido[mes_exp]]
        nombre_mes=f"_{mes_exp}"

    if df_export.empty:
        st.warning("No hay registros.")
    else:
        area_nombre=area_exp.replace(" ","").replace("/","").replace("-","")
        nombre_archivo=f"PQRSDF_{area_nombre}_{anio_exp}{nombre_mes}.xlsx"

        buffer=BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            df_export.to_excel(writer,index=False,sheet_name="PQRSDF")

        buffer.seek(0)

        st.download_button("📥 Descargar archivo",buffer,file_name=nombre_archivo)
