import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 1. CONFIGURACIÓN GENERAL
# ==========================================
# 🔴 PEGA AQUÍ TU ID DE CARPETA (Manten las comillas)
ID_CARPETA_DRIVE = "12xO0e3Yn9idcKwvSvxApEZOmlLOHFPhO" 
NOMBRE_HOJA_CALCULO = "BASE_DE_DATOS_TEG"
ARCHIVO_CONFIG = "data/config_fechas.csv"

st.set_page_config(page_title="Gestión TEG", layout="wide")

# ==========================================
# 2. CONEXIÓN CON GOOGLE (MODO SEGURO)
# ==========================================
def conectar_google():
    """Conecta usando los Secretos de Streamlit (No archivo JSON expuesto)"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Leemos la credencial desde la configuración interna de la nube
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        client_sheets = gspread.authorize(creds)
        service_drive = build('drive', 'v3', credentials=creds)
        return client_sheets, service_drive
    except Exception as e:
        st.error("Error de credenciales. Configure los 'Secrets' en el panel de Streamlit.")
        st.stop()

def subir_archivo_drive(service_drive, ruta_archivo, nombre_archivo):
    file_metadata = {'name': nombre_archivo, 'parents': [ID_CARPETA_DRIVE]}
    media = MediaFileUpload(ruta_archivo, resumable=True)
    file = service_drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

def guardar_en_sheets(client_sheets, datos_lista):
    try:
        sheet = client_sheets.open(NOMBRE_HOJA_CALCULO).sheet1
        # Si la hoja está vacía, creamos los encabezados
        if len(sheet.get_all_values()) == 0:
            encabezados = [
                "FECHA", "PROGRAMA", "TIPO", "MODALIDAD", "TITULO", "LINEA",
                "AUTOR1_NOM", "AUTOR1_CED", "AUTOR1_EMAIL", "AUTOR1_TLF",
                "AUTOR2_NOM", "AUTOR2_CED", "AUTOR2_EMAIL", "AUTOR2_TLF",
                "TUTOR_NOM", "TUTOR_CED", "LINK_EXPEDIENTE", "LINK_TRABAJO"
            ]
            sheet.append_row(encabezados)
        sheet.append_row(datos_lista)
        return True
    except Exception as e:
        st.error(f"Error guardando en Sheets: {e}")
        return False

# ==========================================
# 3. FUNCIONES DE LÓGICA LOCAL
# ==========================================
def cargar_configuracion():
    # Carga las fechas de apertura/cierre
    if os.path.exists(ARCHIVO_CONFIG):
        try:
            df = pd.read_csv(ARCHIVO_CONFIG)
            df['Inicio'] = pd.to_datetime(df['Inicio']).dt.date
            df['Fin'] = pd.to_datetime(df['Fin']).dt.date
            return df
        except: pass
    # Valores por defecto
    return pd.DataFrame({
        "Proceso": ["Proyecto", "TEG"], "Activo": [False, False],
        "Inicio": [date.today(), date.today()], "Fin": [date.today(), date.today()]
    })

def guardar_configuracion(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv(ARCHIVO_CONFIG, index=False)

def generar_pdf_local(lista_imagenes, nombre_archivo):
    # Une las fotos en un PDF
    pdf = FPDF()
    archivos_ok = 0
    for img_up in lista_imagenes:
        if img_up:
            try:
                pdf.add_page()
                img = Image.open(img_up)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save("temp_img.jpg")
                pdf.image("temp_img.jpg", x=10, y=10, w=190)
                archivos_ok += 1
            except: pass
    if archivos_ok > 0:
        pdf.output(nombre_archivo)
        return nombre_archivo
    return None

def generar_constancia(datos):
    # Crea el comprobante para el estudiante
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="CONSTANCIA DE RECEPCION", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(200, 10, txt=f"Tramite: {datos['TIPO']}", ln=True)
    pdf.cell(200, 10, txt=f"Titulo: {datos['TITULO']}", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Documentos cargados y respaldados en la Nube de Google.", ln=True)
    nombre = "Constancia_Inscripcion.pdf"
    pdf.output(nombre)
    return nombre

# ==========================================
# 4. INTERFAZ: PANEL DE ADMINISTRADOR
# ==========================================
df_config = cargar_configuracion()
hoy = date.today()

# Variables de control
act_proy = bool(df_config.loc[0, 'Activo'])
ini_proy, fin_proy = df_config.loc[0, 'Inicio'], df_config.loc[0, 'Fin']
act_teg = bool(df_config.loc[1, 'Activo'])
ini_teg, fin_teg = df_config.loc[1, 'Inicio'], df_config.loc[1, 'Fin']

# ¿Está abierto hoy?
abierto_proy = act_proy and (ini_proy <= hoy <= fin_proy)
abierto_teg = act_teg and (ini_teg <= hoy <= fin_teg)

st.sidebar.title("Panel Coordinador")
password = st.sidebar.text_input("Contraseña", type="password")

if password == "admin123":
    st.sidebar.success("Modo Admin Activo")
    st.sidebar.markdown("---")
    
    st.sidebar.header("Configurar PROYECTO")
    n_act_p = st.sidebar.checkbox("Activar Proyecto", value=act_proy)
    n_ini_p = st.sidebar.date_input("Inicio P.", ini_proy)
    n_fin_p = st.sidebar.date_input("Fin P.", fin_proy)
    
    st.sidebar.markdown("---")
    
    st.sidebar.header("Configurar TEG")
    n_act_t = st.sidebar.checkbox("Activar TEG", value=act_teg)
    n_ini_t = st.sidebar.date_input("Inicio T.", ini_teg)
    n_fin_t = st.sidebar.date_input("Fin T.", fin_teg)
    
    if st.sidebar.button("💾 Guardar Cambios"):
        df_config.loc[0] = ["Proyecto", n_act_p, n_ini_p, n_fin_p]
        df_config.loc[1] = ["TEG", n_act_t, n_ini_t, n_fin_t]
        guardar_configuracion(df_config)
        st.success("Configuración guardada.")
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.info("Nota: La base de datos ahora reside en Google Sheets, no se descarga desde aquí.")

# ==========================================
# 5. INTERFAZ: FORMULARIO ESTUDIANTE
# ==========================================
st.title("☁️ Sistema de Inscripciones (Nube)")

if not abierto_proy and not abierto_teg:
    st.warning("⚠️ No hay procesos de inscripción abiertos actualmente.")
    st.stop()

# Selección de Trámite
opciones = []
if abierto_proy: opciones.append("Proyecto")
if abierto_teg: opciones.append("TEG")

tipo_tramite = st.selectbox("Seleccione el trámite:", opciones)
st.info(f"Usted está inscribiendo: **{tipo_tramite}**")
st.markdown("---")

# Datos del Trabajo
c_prog, c_mod = st.columns(2)
programa = c_prog.selectbox("Programa Académico", ["Ing. Civil", "Ing. Industrial", "Ing. Mecánica", "D. Empresarial", "Enfermería", "Artes", "Fisioterapia"])
modalidad = c_mod.radio("Modalidad", ["Individual", "Pareja"])
titulo = st.text_input("Título del Trabajo")
linea = st.text_input("Línea de Investigación")

st.markdown("---")

# --- AUTOR 1 ---
st.subheader("Datos Autor 1 (Principal)")
col1, col2 = st.columns(2)
a1_nom = col1.text_input("Nombres A1")
a1_ced = col2.text_input("Cédula A1")
a1_ema = col1.text_input("Correo A1")
a1_tlf = col2.text_input("Teléfono A1")

st.markdown("**Requisitos A1 (Imágenes):**")
f1_pla = st.file_uploader("1. Planilla Inscripción (A1)", type=['jpg','png','jpeg'], key="f1a")
f1_ced = st.file_uploader("2. Cédula (A1)", type=['jpg','png','jpeg'], key="f1b")
f1_com = st.file_uploader("3. Constancia Comunidad (A1)", type=['jpg','png','jpeg'], key="f1c")
f1_ser = st.file_uploader("4. Constancia Servicio (A1)", type=['jpg','png','jpeg'], key="f1d")
f1_rec = st.file_uploader("📄 Récord Académico A1