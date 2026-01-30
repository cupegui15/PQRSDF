import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(
    page_title="PQRSDF | Tablero de Control",
    layout="wide"
)

st.markdown("## 📊 Tablero de Control PQRSDF")
st.caption("Análisis y seguimiento – Diseño tipo formulario de monitoreos")

# ==================================================
# FUENTE DE DATOS (GOOGLE SHEETS - CSV)
# ==================================================
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1FjApsoQIvz_nmaRCbO7NDD7N9M_noQaH/"
    "export?format=csv&gid=925681863"
)

@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(CSV_URL)

df = load_data()

# ==================================================
# LIMPIEZA Y PREPARACIÓN
# ==================================================
df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')
df = df.dropna(subset=['AÑO', 'Mes'])

# Mes a texto
meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
df['Mes_nombre'] = df['Mes'].map(meses)

# Semestre
df['Semestre'] = df['Mes'].apply(
    lambda x: "Semestre 1" if x <= 6 else "Semestre 2"
)

orden_meses = list(meses.values())

# ==================================================
# SIDEBAR – NAVEGACIÓN + FILTROS
# ==================================================
with st.sidebar:

    st.markdown("### 🧭 Navegación")

    dashboard = st.radio(
        label="",
        options=[
            "Dashboard por Área",
            "Dashboard En Curso",
            "Dashboard No Cumple"
        ]
    )

    st.divider()

    st.markdown("### 🎛️ Filtros")

    anio = st.multiselect(
        "Año",
        sorted(df['AÑO'].unique())
    )

    semestre = st.multiselect(
        "Semestre",
        ["Semestre 1", "Semestre 2"]
    )

    mes = st.multiselect(
        "Mes",
        orden_meses
    )

    categoria = st.multiselect(
        "Categoría",
        sorted(df['Categoría'].dropna().unique())
    )

# ==================================================
# APLICACIÓN DE FILTROS
# ==================================================
df_f = df.copy()

if anio:
    df_f = df_f[df_f['AÑO'].isin(anio)]

if semestre:
    df_f = df_f[df_f['Semestre'].isin(semestre)]

if mes:
    df_f = df_f[df_f['Mes_nombre'].isin(mes)]

if categoria:
    df_f = df_f[df_f['Categoría'].isin(categoria)]

# ==================================================
# KPIs SUPERIORES (ESTILO FORMULARIO)
# ==================================================
st.markdown("### 📌 Indicadores generales")

k1, k2, k3, k4 = st.columns(4)

k1.metric("📄 Total PQRSDF", len(df_f))
k2.metric("🏢 Áreas", df_f['Area principal'].nunique())
k3.metric("📂 Categorías", df_f['Categoría'].nunique())
k4.metric("🗓️ Periodos", df_f[['AÑO', 'Mes_nombre']].drop_duplicates().shape[0])

st.divider()

# ==================================================
# DASHBOARD POR ÁREA
# ==================================================
if dashboard == "Dashboard por Área":

    st.markdown("## 🏢 Comportamiento por Área")
    st.caption("Cantidad de PQRSDF por área en el periodo seleccionado")

    df_area = (
        df_f
        .groupby('Area principal', as_index=False)
        .size()
        .rename(columns={'size': 'Cantidad PQRSDF'})
        .sort_values('Cantidad PQRSDF', ascending=False)
    )

    fig = px.bar(
        df_area,
        x='Area principal',
        y='Cantidad PQRSDF',
        text='Cantidad PQRSDF',
        color='Cantidad PQRSDF',
        color_continuous_scale='Blues'
    )

    fig.update_layout(
        xaxis_title="Área",
        yaxis_title="Cantidad de PQRSDF",
        xaxis_tickangle=-40
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_area, use_container_width=True)

# ==================================================
# DASHBOARD EN CURSO
# ==================================================
elif dashboard == "Dashboard En Curso":

    st.markdown("## ⏳ PQRSDF En Curso")
    st.caption("Casos que aún no se encuentran cerrados")

    df_curso = df_f[df_f['Estado'].str.lower() != 'cerrado']

    c1, c2 = st.columns(2)
    c1.metric("⏳ Casos en curso", len(df_curso))
    c2.metric("🏢 Áreas involucradas", df_curso['Area principal'].nunique())

    df_area_curso = (
        df_curso
        .groupby('Area principal', as_index=False)
        .size()
        .rename(columns={'size': 'Casos en curso'})
        .sort_values('Casos en curso', ascending=False)
    )

    fig = px.bar(
        df_area_curso,
        x='Area principal',
        y='Casos en curso',
        text='Casos en curso',
        color='Casos en curso',
        color_continuous_scale='Oranges'
    )

    fig.update_layout(xaxis_tickangle=-40)

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_area_curso, use_container_width=True)

# ==================================================
# DASHBOARD NO CUMPLE (SLA)
# ==================================================
elif dashboard == "Dashboard No Cumple":

    st.markdown("## ❌ PQRSDF No Cumple SLA")
    st.caption("Áreas que no cumplieron los tiempos de respuesta")

    df_nc = df_f[
        df_f['SLA']
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(['no cumple', 'nocumple', 'no'])
    ]

    if df_nc.empty:
        st.success("✅ No se registran incumplimientos de SLA en el periodo seleccionado.")
        st.stop()

    c1, c2 = st.columns(2)
    c1.metric("❌ Casos No Cumple", len(df_nc))
    c2.metric("🏢 Áreas críticas", df_nc['Area principal'].nunique())

    df_area_nc = (
        df_nc
        .groupby('Area principal', as_index=False)
        .size()
        .rename(columns={'size': 'No Cumple SLA'})
        .sort_values('No Cumple SLA', ascending=False)
    )

    fig = px.bar(
        df_area_nc,
        x='Area principal',
        y='No Cumple SLA',
        text='No Cumple SLA',
        color='No Cumple SLA',
        color_continuous_scale='Reds'
    )

    fig.update_layout(xaxis_tickangle=-40)

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_nc[
            [
                'num caso',
                'AÑO',
                'Mes_nombre',
                'Categoría',
                'Area principal',
                'Estado',
                'SLA'
            ]
        ],
        use_container_width=True
    )
