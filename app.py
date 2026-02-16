import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(
    page_title="PQRSDF | Universidad del Rosario",
    layout="wide",
    page_icon="📋"
)

URL_LOGO_UR = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY0ZMIXOVuzLond_jNv713shc6TmUWej0JDQ&s"

st.sidebar.image(URL_LOGO_UR, width=120)

pagina = st.sidebar.radio(
    "",
    [
        "📌 Seguimiento Diario",
        "🎯 Indicador por Área",
        "🔎 Búsqueda de Caso",
        "📥 Exportación mensual",
        "📧 Notificaciones"
    ]
)

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
sheet = sh.worksheet("PQRSDF")

@st.cache_data(ttl=300)
def cargar():
    return pd.DataFrame(sheet.get_all_records())

df = cargar()

# ==================================================
# LIMPIEZA GENERAL
# ==================================================
df.columns = df.columns.str.strip()
df['Estado'] = df['Estado'].astype(str).str.lower().str.strip()
df['Categoría'] = df['Categoría'].astype(str).str.lower().str.strip()
df['SLA'] = df['SLA'].astype(str).str.lower().str.strip()
df['Fecha cierre'] = pd.to_datetime(df['Fecha cierre'], errors='coerce')

# ==================================================
# 📌 SEGUIMIENTO DIARIO
# ==================================================
if pagina == "📌 Seguimiento Diario":

    st.markdown("## 📌 Seguimiento de Casos")

    col1, col2 = st.columns(2)

    with col1:
        area = st.selectbox("Área", ["Todas"] + sorted(df['Area principal'].dropna().unique()))
    with col2:
        anio = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    df_seg = df[df['AÑO'] == anio].copy()

    if area != "Todas":
        df_seg = df_seg[df_seg['Area principal'] == area]

    hoy = pd.Timestamp.today()
    df_seg['Dias_restantes'] = (df_seg['Fecha cierre'] - hoy).dt.days

    proximos = df_seg[
        (df_seg['Estado'] != "cerrado") &
        (df_seg['Dias_restantes'] <= 3) &
        (df_seg['Dias_restantes'] >= 0)
    ]

    vencidos = df_seg[
        (df_seg['Estado'] != "cerrado") &
        (df_seg['Dias_restantes'] < 0)
    ]

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total", len(df_seg))
    c2.metric("En Proceso", len(df_seg[df_seg['Estado'] != "cerrado"]))
    c3.metric("Cerrados", len(df_seg[df_seg['Estado'] == "cerrado"]))
    c4.metric("No Cumplen SLA", len(df_seg[df_seg['SLA'].str.contains("no")]))
    c5.metric("Próximos a Vencer", len(proximos))
    c6.metric("🚨 Vencidos", len(vencidos))

    if not proximos.empty:
        st.markdown("### ⚠️ Próximos a vencer")
        st.dataframe(
            proximos[['num caso','Area principal','Fecha cierre','Dias_restantes']],
            use_container_width=True
        )

    if not vencidos.empty:
        st.markdown("### 🚨 Vencidos en curso")
        st.dataframe(
            vencidos[['num caso','Area principal','Fecha cierre','Dias_restantes']],
            use_container_width=True
        )

# ==================================================
# 🎯 INDICADOR POR ÁREA
# ==================================================
elif pagina == "🎯 Indicador por Área":

    st.markdown("## 🎯 Indicador de Cumplimiento SLA")

    anio = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    df_ind = df[df['AÑO'] == anio].copy()

    categorias_validas = [
        "petición",
        "queja",
        "reclamo",
        "derecho de petición"
    ]

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

    resumen['Indicador (%)'] = round(
        (resumen['Cumplen']/resumen['Total'])*100,
        2
    )

    st.dataframe(resumen, use_container_width=True)

    fig = px.bar(
        resumen,
        x='Area principal',
        y='Indicador (%)',
        text='Indicador (%)',
        title="Cumplimiento SLA por Área"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# 🔎 BÚSQUEDA DE CASO
# ==================================================
elif pagina == "🔎 Búsqueda de Caso":

    st.markdown("## 🔎 Buscar Caso")

    numero = st.text_input("Número de caso")

    if numero:
        resultado = df[df['num caso'].astype(str) == numero.strip()]
        if resultado.empty:
            st.warning("No se encontró el caso.")
        else:
            st.dataframe(resultado, use_container_width=True)

# ==================================================
# 📥 EXPORTACIÓN
# ==================================================
elif pagina == "📥 Exportación mensual":

    st.markdown("## 📥 Exportación por Área y Año")

    area = st.selectbox("Área", sorted(df['Area principal'].dropna().unique()))
    anio = st.selectbox("Año", sorted(df['AÑO'].dropna().unique()))

    df_exp = df[
        (df['Area principal'] == area) &
        (df['AÑO'] == anio)
    ]

    if df_exp.empty:
        st.warning("No hay datos.")
    else:
        nombre_archivo = f"PQRSDF_{area.replace(' ','_')}_{anio}.xlsx"

        buffer = BytesIO()
        df_exp.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "📥 Descargar archivo",
            buffer,
            file_name=nombre_archivo
        )

# ==================================================
# 📧 NOTIFICACIONES CON FIRMA Y COLUMNAS ADICIONALES
# ==================================================
elif pagina == "📧 Notificaciones":

    st.markdown("## 📧 Envío Manual de Notificaciones")

    if st.button("📨 Enviar Notificaciones"):

        hoy = pd.Timestamp.today().normalize()

        df_notif = df[df['Estado'].str.lower() != "cerrado"].copy()

        # Asegurar fecha datetime
        df_notif['Fecha cierre'] = pd.to_datetime(df_notif['Fecha cierre'], errors='coerce')

        df_notif['Dias_restantes'] = (df_notif['Fecha cierre'] - hoy).dt.days

        if df_notif.empty:
            st.warning("No hay casos en proceso.")
            st.stop()

        areas = df_notif['Area principal'].dropna().unique()
        enviados = 0

        # ==============================
        # FIRMA BASE64
        # ==============================
        
        FIRMA_BASE64 = FIRMA_BASE64 = "data:image/jpeg;base64,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NPue4MgLoSmNgAwMcnGK+BlODnGa+jPgl+3H4y+BPhfwnoeiaNod5b+G9audbtpb6KUySyT2r2zxyFZFBQLIxGADnGcjqAavx8/ZH8L/AA4+B9l8SvAnxMh+IWjxa6/hrVSumSWYgvAhk/dl2O9cL1wMhlPcgfL1eqX/AO0Tr2ofAvUPhY+n6cmh3viVvE8l0iOLkXBi8vywQ23ywOQCpOT16V5XQBu+CfBmpfEHxbovhrRo1m1fWLyGxtInbarSyOEXLHgDJHNffPgD4a/Db9nT4G/H/wAP+O7m2+K2k2V9odlq7+Gh9nn028aa6R44JpVwXjaNckcHOOO/5/eGfE2oeD/EGla5pFw9lqumXUd5a3MZGY5Y2Do4BBGQwB/Cva/jZ+2n4w+N3g+fw5eaF4Y8M2eoXg1LWpPDem/ZJNZvAMC4um3Eu/JPYZOcUAeEaobU6ldGy837H5reR55Bk8vPy7scbsYzjjOa/qfr+VdjuOa/qooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACvxW/4LV/8AJ0/hb/sTLX/0uvqKKAPgCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAK/qooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA//9k="

        for area in areas:

            df_area = df_notif[df_notif['Area principal'] == area].copy()

            if df_area.empty:
                continue

            df_area = df_area.sort_values("Dias_restantes")

            # ==============================
            # TABLA HTML
            # ==============================
            tabla_html = """
            <table border='1' cellpadding='6' cellspacing='0' 
            style='border-collapse:collapse; font-family:Arial; font-size:13px;'>

            <tr style='background-color:#9B0029;color:white;'>
                <th>Caso</th>
                <th>Categoría</th>
                <th>Ext. tiempos</th>
                <th>Fecha Vencimiento</th>
                <th>Días Restantes</th>
            </tr>
            """

            for _, row in df_area.iterrows():

                dias = row['Dias_restantes']
                fecha = row['Fecha cierre']
                categoria = row.get('Categoría', '')
                ext_tiempos = row.get('Ext de tiempos', '')

                color = "background-color:#ffcccc;" if pd.notnull(dias) and dias < 0 else ""

                tabla_html += f"""
                <tr style='{color}'>
                    <td>{row['num caso']}</td>
                    <td>{categoría}</td>
                    <td>{ext_tiempos}</td>
                    <td>{fecha.date() if pd.notnull(fecha) else ''}</td>
                    <td>{dias if pd.notnull(dias) else ''}</td>
                </tr>
                """

            tabla_html += "</table>"

            # ==============================
            # CUERPO DEL CORREO
            # ==============================
            cuerpo = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">

            <p>Buen día,</p>

            <p>Estos son los casos en proceso del área <strong>{area}</strong>:</p>

            {tabla_html}

            <p><strong>Los casos marcados en rojo están vencidos.</strong></p>

            <p>Se adjunta archivo Excel con el detalle completo del área.</p>

            <br><br>

            <img src="{FIRMA_BASE64}" width="600">

            </body>
            </html>
            """

            # ==============================
            # CREAR MENSAJE
            # ==============================
            msg = MIMEMultipart()
            msg['From'] = st.secrets["EMAIL_USER"]
            msg['To'] = "oportunidadesdemejora@urosario.edu.co"
            msg['Cc'] = "oportunidadesdemejora@urosario.edu.co"
            msg['Subject'] = f"PQRSDF - Casos en proceso - {area}"

            msg.attach(MIMEText(cuerpo, 'html'))

            # ==============================
            # ADJUNTAR EXCEL
            # ==============================
            buffer = BytesIO()
            df_area.to_excel(buffer, index=False)
            buffer.seek(0)

            nombre_archivo = f"PQRSDF_{area}.xlsx"

            adj = MIMEApplication(buffer.read(), Name=nombre_archivo)
            adj['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
            msg.attach(adj)

            # ==============================
            # ENVIAR
            # ==============================
            try:
                server = smtplib.SMTP("smtp.office365.com", 587)
                server.starttls()
                server.login(
                    st.secrets["EMAIL_USER"],
                    st.secrets["EMAIL_PASSWORD"]
                )
                server.send_message(msg)
                server.quit()

                enviados += 1

            except Exception as e:
                st.error(f"Error enviando correo para {area}: {e}")
                continue

        st.success(f"✅ Se enviaron {enviados} notificaciones.")
