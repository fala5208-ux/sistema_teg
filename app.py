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
# 1. CONFIGURACIÓN DE CONEXIÓN (EDITAR AQUÍ)
# ==========================================
ID_CARPETA_DRIVE = "12xO0e3Yn9idcKwvSvxApEZOmlLOHFPhO" 
NOMBRE_HOJA_CALCULO = "BASE_DE_DATOS_TEG"
ARCHIVO_JSON = "robot_key.json"
ARCHIVO_CONFIG = "data/config_fechas.csv"

st.set_page_config(page_title="Gestión TEG", layout="wide")

# --- CONEXIÓN CON GOOGLE ---
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        client_sheets = gspread.authorize(creds)
        service_drive = build('drive', 'v3', credentials=creds)
        return client_sheets, service_drive
    except Exception as e:
        st.error("Error de credenciales. Verifique el archivo robot_key.json o los 'Secrets' en la nube.")
        st.stop()

def subir_archivo_drive(service_drive, ruta_archivo, nombre_archivo):
    file_metadata = {'name': nombre_archivo, 'parents': [ID_CARPETA_DRIVE]}
    media = MediaFileUpload(ruta_archivo, resumable=True)
    file = service_drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

def guardar_en_sheets(client_sheets, datos_lista):
    try:
        sheet = client_sheets.open(NOMBRE_HOJA_CALCULO).sheet1
        if len(sheet.get_all_values()) == 0:
            # Encabezados de la base de datos (con datos completos del tutor)
            encabezados = [
                "FECHA", "PROGRAMA", "TIPO", "MODALIDAD", "TITULO", "LINEA",
                "AUTOR1_NOM", "AUTOR1_CED", "AUTOR1_EMAIL", "AUTOR1_TLF",
                "AUTOR2_NOM", "AUTOR2_CED", "AUTOR2_EMAIL", "AUTOR2_TLF",
                "TUTOR_NOM", "TUTOR_CED", "TUTOR_EMAIL", "TUTOR_TLF", # <--- Tutor completo
                "LINK_EXPEDIENTE", "LINK_TRABAJO"
            ]
            sheet.append_row(encabezados)
        sheet.append_row(datos_lista)
        return True
    except Exception as e:
        st.error(f"Error guardando en Sheets: {e}")
        return False

# --- FUNCIONES LOCALES (PDF y CONTROL) ---
def cargar_configuracion():
    if os.path.exists("data/config_fechas.csv"):
        try:
            df = pd.read_csv("data/config_fechas.csv")
            df['Inicio'] = pd.to_datetime(df['Inicio']).dt.date
            df['Fin'] = pd.to_datetime(df['Fin']).dt.date
            return df
        except: pass
    return pd.DataFrame({
        "Proceso": ["Proyecto", "TEG"], "Activo": [False, False],
        "Inicio": [date.today(), date.today()], "Fin": [date.today(), date.today()]
    })

def guardar_configuracion(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/config_fechas.csv", index=False)

def generar_pdf_local(lista_imagenes, nombre_archivo):
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
act_proy = bool(df_config.loc[0, 'Activo'])
ini_proy, fin_proy = df_config.loc[0, 'Inicio'], df_config.loc[0, 'Fin']
act_teg = bool(df_config.loc[1, 'Activo'])
ini_teg, fin_teg = df_config.loc[1, 'Inicio'], df_config.loc[1, 'Fin']
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

# 5. INTERFAZ ESTUDIANTE (Formulario)
st.title("☁️ Sistema de Inscripciones (Nube)")

if not abierto_proy and not abierto_teg:
    st.warning("⚠️ No hay procesos de inscripción abiertos actualmente.")
    st.stop()

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
f1_rec = st.file_uploader("📄 Récord Académico A1 (PDF)", type=['pdf'], key="f1e")

# --- AUTOR 2 (CONDICIONAL) ---
a2_nom, a2_ced, a2_ema, a2_tlf = "", "", "", ""
f2_pla, f2_ced, f2_com, f2_ser, f2_rec = None, None, None, None, None

if modalidad == "Pareja": # <--- ESTO DEBE ABRIR LA SECCIÓN DEL SEGUNDO AUTOR
    st.markdown("---")
    st.subheader("Datos Autor 2")
    col3, col4 = st.columns(2) # <--- Definición de columnas
    a2_nom = col3.text_input("Nombres A2") # <--- Uso de variables de columna
    a2_ced = col4.text_input("Cédula A2")
    a2_ema = col3.text_input("Correo A2")
    a2_tlf = col4.text_input("Teléfono A2")
    
    st.markdown("**Requisitos A2 (Imágenes):**")
    f2_pla = st.file_uploader("1. Planilla Inscripción (A2)", type=['jpg','png','jpeg'], key="f2a")
    f2_ced = st.file_uploader("2. Cédula (A2)", type=['jpg','png','jpeg'], key="f2b")
    f2_com = st.file_uploader("3. Constancia Comunidad (A2)", type=['jpg','png','jpeg'], key="f2c")
    f2_ser = st.file_uploader("4. Constancia Servicio (A2)", type=['jpg','png','jpeg'], key="f2d")
    f2_rec = st.file_uploader("📄 Récord Académico A2 (PDF)", type=['pdf'], key="f2e")

st.markdown("---")

# --- TUTOR --- (AQUÍ ESTABA EL CAMPO FALTANTE)
st.subheader("🎓 Datos del Tutor")
col_t1, col_t2 = st.columns(2)
t_nom = col_t1.text_input("Nombre Tutor")
t_ced = col_t2.text_input("Cédula Tutor")
t_ema = col_t1.text_input("Correo Tutor") # <--- CAMPO AGREGADO
t_tlf = col_t2.text_input("Teléfono Tutor") # <--- CAMPO AGREGADO

st.markdown("**Documentos del Tutor:**")
f_tut_car = st.file_uploader("Carta Aceptación Tutor", type=['jpg','png'], key="ft1")
f_tut_ced = st.file_uploader("Cédula Tutor", type=['jpg','png'], key="ft2")

f_teg_apto = None
if tipo_tramite == "TEG":
    st.warning("Requisito Especial TEG")
    f_teg_apto = st.file_uploader("Carta Apto Defensa (Solo TEG)", type=['jpg','png'], key="ft3")

st.markdown("**Archivo Final:**")
f_tesis = st.file_uploader("📂 Cargar Tomo del Trabajo (WORD)", type=['docx','doc'])

# ==========================================
# 6. BOTÓN DE ENVÍO Y PROCESAMIENTO
# ==========================================
if st.button("Enviar Inscripción a la Nube"):
    if not titulo or not a1_ced or not f_tesis:
        st.error("❌ Faltan datos obligatorios.")
    else:
        with st.spinner("Conectando con Google y subiendo archivos..."):
            try:
                sheets, drive = conectar_google()
                
                # 1. Generar Expediente PDF
                imgs = [f1_pla, f1_ced, f_tut_car, f_tut_ced, f1_com, f1_ser, f_teg_apto]
                if modalidad == "Pareja": imgs.extend([f2_pla, f2_ced, f2_com, f2_ser])
                
                nombre_exp = f"EXP_{tipo_tramite}_{a1_ced}.pdf"
                path_exp = generar_pdf_local(imgs, nombre_exp)
                
                link_exp = "Sin Soportes"
                if path_exp:
                    link_exp = subir_archivo_drive(drive, path_exp, nombre_exp)
                    os.remove(path_exp)
                
                # 2. Subir Tesis Word
                nombre_tesis = f"TESIS_{tipo_tramite}_{a1_ced}.docx"
                with open(nombre_tesis, "wb") as f: f.write(f_tesis.getbuffer())
                link_tesis = subir_archivo_drive(drive, nombre_tesis, nombre_tesis)
                os.remove(nombre_tesis)
                
                # 3. Guardar en Sheets (Con datos completos del tutor)
                datos = [
                    datetime.now().strftime("%Y-%m-%d"), programa, tipo_tramite, modalidad, titulo, linea,
                    a1_nom, a1_ced, a1_ema, a1_tlf,
                    a2_nom, a2_ced, a2_ema, a2_tlf,
                    t_nom, t_ced, t_ema, t_tlf, # <--- DATOS DEL TUTOR AGREGADOS
                    link_exp, link_tesis
                ]
                guardar_en_sheets(sheets, datos)
                
                # 4. Generar Constancia
                datos_c = {"TIPO": tipo_tramite, "TITULO": titulo}
                path_c = generar_constancia(datos_c)
                
                st.success("✅ ¡Inscripción Exitosa y Guardada en Drive!")
                st.balloons()
                with open(path_c, "rb") as f:
                    st.download_button("Descargar Constancia", f, "Constancia.pdf")
                    
            except Exception as e:
                st.error(f"Error de conexión: {e}")
