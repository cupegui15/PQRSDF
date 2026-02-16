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
# 📧 NOTIFICACIONES
# ==================================================
elif pagina == "📧 Notificaciones":

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    st.markdown("## 📧 Envío Manual de Notificaciones")

    # Cargar responsables
    responsables_df = pd.read_excel("responsables.xlsx")
    responsables_df.columns = responsables_df.columns.str.strip()

    if st.button("📨 Enviar Notificaciones"):

        hoy = pd.Timestamp.today().normalize()

        df_notif = df[df['Estado'].str.lower() != "cerrado"].copy()
        df_notif['Fecha cierre'] = pd.to_datetime(df_notif['Fecha cierre'], errors='coerce')
        df_notif['Dias_restantes'] = (df_notif['Fecha cierre'] - hoy).dt.days

        if df_notif.empty:
            st.warning("No hay casos en proceso.")
            st.stop()

        areas = df_notif['Area principal'].dropna().unique()
        enviados = 0

        # Correos en copia
        CC_CORREOS = [
            "cristian.upegui@urosario.edu.co",
            "sandrapa.guzman@urosario.edu.co",
            "yesid.garzon@urosario.edu.co",
            "oportunidadesdemejora@urosario.edu.co"
        ]

        for area in areas:

            df_area = df_notif[df_notif['Area principal'] == area]

            if df_area.empty:
                continue

            dependencias = df_area['Dependencia'].dropna().unique()
            destinatarios = []

            # ==============================
            # BUSCAR RESPONSABLES
            # ==============================
            for dep in dependencias:

                filtro_resp = responsables_df[
                    (responsables_df['Area principal'].str.strip().str.lower() == str(area).strip().lower()) &
                    (responsables_df['Dependencia'].str.strip().str.lower() == str(dep).strip().lower())
                ]

                if not filtro_resp.empty:

                    correos_raw = filtro_resp.iloc[0]['Responsable']

                    if pd.notnull(correos_raw):

                        lista_correos = str(correos_raw).split("//")

                        for correo in lista_correos:
                            correo_limpio = correo.strip()
                            if correo_limpio:
                                destinatarios.append(correo_limpio)

            # Fallback
            if not destinatarios:
                destinatarios = ["oportunidadesdemejora@urosario.edu.co"]

            destinatarios = list(set(destinatarios))

            # ==============================
            # TABLA HTML
            # ==============================
            tabla_html = """
            <table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse; font-family:Arial; font-size:13px;'>
            <tr style='background-color:#9B0029;color:white;'>
                <th>Caso</th>
                <th>Categoría</th>
                <th>Ext de tiempos</th>
                <th>Fecha cierre</th>
                <th>Días Restantes</th>
            </tr>
            """

            df_area = df_area.sort_values("Dias_restantes")

            for _, row in df_area.iterrows():

                dias = row['Dias_restantes']
                fecha = row['Fecha cierre']
                categoria = row.get('Categoría', '')
                ext_tiempos = row.get('Ext de tiempos', '')

                color = "background-color:#ffcccc;" if pd.notnull(dias) and dias < 0 else ""

                tabla_html += f"""
                <tr style='{color}'>
                    <td>{row['num caso']}</td>
                    <td>{categoria}</td>
                    <td>{ext_tiempos}</td>
                    <td>{fecha.strftime('%Y-%m-%d') if pd.notnull(fecha) else ''}</td>
                    <td>{dias if pd.notnull(dias) else ''}</td>
                </tr>
                """

            tabla_html += "</table>"

            # ==============================
            # ARMAR CORREO
            # ==============================

            mensaje = MIMEMultipart("alternative")
            mensaje["Subject"] = f"🔔 Notificación PQRSDF - {area}"
            mensaje["From"] = "oportunidadesdemejora@urosario.edu.co"
            mensaje["To"] = ", ".join(destinatarios)
            mensaje["Cc"] = ", ".join(CC_CORREOS)

            html = f"""
            <html>
            <body style="font-family:Arial;">
                <p>Estimados,</p>

                <p>Se relacionan los casos PQRSDF pendientes de gestión para el área <b>{area}</b>:</p>

                {tabla_html}

                <br>
                <p>Por favor revisar y gestionar dentro de los tiempos establecidos.</p>

                <p style="color:#9B0029;"><b>Oficina de Oportunidades de Mejora</b></p>
            </body>
            </html>
            """

            parte_html = MIMEText(html, "html")
            mensaje.attach(parte_html)

            # ==============================
            # ENVÍO SMTP
            # ==============================

            try:
                with smtplib.SMTP("smtp.office365.com", 587) as server:
                    server.starttls()
                    server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASSWORD"])
                    server.sendmail(
                        mensaje["From"],
                        destinatarios + CC_CORREOS,
                        mensaje.as_string()
                    )

                enviados += 1

            except Exception as e:
                st.error(f"Error enviando correo a {area}: {e}")

        if enviados > 0:
            st.success(f"✅ Notificaciones enviadas correctamente a {enviados} áreas.")
        else:
            st.warning("No se enviaron notificaciones.")
