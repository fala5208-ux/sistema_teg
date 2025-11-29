import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF
from PIL import Image
from io import BytesIO # Necesario para generar el Excel en memoria

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Gestión TEG", layout="wide")

# --- RUTAS ---
CARPETA_EXPEDIENTES = "archivos/expedientes"
CARPETA_TESIS = "archivos/tesis"
ARCHIVO_DB = "data/base_datos.xlsx" # CAMBIO: Ahora es .xlsx
ARCHIVO_CONFIG = "data/config_fechas.csv"

# Crear carpetas si no existen
os.makedirs(CARPETA_EXPEDIENTES, exist_ok=True)
os.makedirs(CARPETA_TESIS, exist_ok=True)
os.makedirs("data", exist_ok=True)

# --- DEFINICIÓN DE COLUMNAS (Orden Oficial) ---
COLUMNAS_BD = [
    "FECHA_REGISTRO", "PROGRAMA_ACADEMICO", "TIPO_TRAMITE", "MODALIDAD",
    "TITULO_PROYECTO", "LINEA_INVESTIGACION",
    "AUTOR1_CEDULA", "AUTOR1_NOMBRE", "AUTOR1_TLF", "AUTOR1_CORREO",
    "AUTOR2_CEDULA", "AUTOR2_NOMBRE", "AUTOR2_TLF", "AUTOR2_CORREO",
    "TUTOR_NOMBRE", "TUTOR_CEDULA",
    "RUTA_EXPEDIENTE", "RUTA_TRABAJO"
]

# --- FUNCIONES ---

def cargar_configuracion():
    if os.path.exists(ARCHIVO_CONFIG):
        try:
            df = pd.read_csv(ARCHIVO_CONFIG)
            df['Inicio'] = pd.to_datetime(df['Inicio']).dt.date
            df['Fin'] = pd.to_datetime(df['Fin']).dt.date
            return df
        except:
            pass
    return pd.DataFrame({
        "Proceso": ["Proyecto", "TEG"],
        "Activo": [False, False],
        "Inicio": [date.today(), date.today()],
        "Fin": [date.today(), date.today()]
    })

def guardar_configuracion(df):
    df.to_csv(ARCHIVO_CONFIG, index=False)

def guardar_en_bd(datos_dict):
    """Guarda los datos en un archivo EXCEL (.xlsx) real"""
    # 1. Crear el DataFrame con la nueva fila
    df_nuevo = pd.DataFrame([datos_dict])
    
    # 2. Asegurar que existan todas las columnas en el orden correcto
    for col in COLUMNAS_BD:
        if col not in df_nuevo.columns:
            df_nuevo[col] = ""
    df_nuevo = df_nuevo[COLUMNAS_BD]

    # 3. Leer el Excel existente o crear uno nuevo
    if os.path.exists(ARCHIVO_DB):
        try:
            # Leemos el archivo actual
            df_existente = pd.read_excel(ARCHIVO_DB)
            # Pegamos la nueva fila debajo
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        except:
            # Si da error leyendo, sobrescribimos (caso raro)
            df_final = df_nuevo
    else:
        df_final = df_nuevo
    
    # 4. Guardar de nuevo el Excel completo
    df_final.to_excel(ARCHIVO_DB, index=False)

def generar_pdf_expediente(lista_imagenes, nombre_archivo):
    pdf = FPDF()
    archivos_procesados = 0
    for imagen_upload in lista_imagenes:
        if imagen_upload is not None:
            try:
                pdf.add_page()
                img = Image.open(imagen_upload)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img_path = f"temp_{imagen_upload.name}"
                img.save(img_path)
                pdf.image(img_path, x=10, y=10, w=190)
                img.close()
                os.remove(img_path)
                archivos_procesados += 1
            except Exception as e:
                continue
    
    if archivos_procesados > 0:
        ruta_completa = os.path.join(CARPETA_EXPEDIENTES, nombre_archivo)
        pdf.output(ruta_completa)
        return ruta_completa
    else:
        return None

def generar_constancia(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="CONSTANCIA DE RECEPCION", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(200, 10, txt=f"Tramite: {datos['TIPO_TRAMITE']}", ln=True)
    pdf.cell(200, 10, txt=f"Titulo: {datos['TITULO_PROYECTO']}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, txt="Autores:", ln=True)
    pdf.cell(200, 10, txt=f"- {datos['AUTOR1_NOMBRE']} ({datos['AUTOR1_CEDULA']})", ln=True)
    if datos['MODALIDAD'] == 'Pareja':
        pdf.cell(200, 10, txt=f"- {datos['AUTOR2_NOMBRE']} ({datos['AUTOR2_CEDULA']})", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, txt="Recaudos digitales recibidos satisfactoriamente.", ln=True, align='C')
    nombre = f"Constancia_{datos['AUTOR1_CEDULA']}.pdf"
    pdf.output(nombre)
    return nombre

# --- CONTROL Y FECHAS ---
df_config = cargar_configuracion()
hoy = date.today()

act_proy = bool(df_config.loc[0, 'Activo'])
ini_proy, fin_proy = df_config.loc[0, 'Inicio'], df_config.loc[0, 'Fin']
act_teg = bool(df_config.loc[1, 'Activo'])
ini_teg, fin_teg = df_config.loc[1, 'Inicio'], df_config.loc[1, 'Fin']

abierto_proy = act_proy and (ini_proy <= hoy <= fin_proy)
abierto_teg = act_teg and (ini_teg <= hoy <= fin_teg)

# --- PANEL ADMIN ---
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
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("💾 Guardar Cambios"):
        df_config.loc[0] = ["Proyecto", n_act_p, n_ini_p, n_fin_p]
        df_config.loc[1] = ["TEG", n_act_t, n_ini_t, n_fin_t]
        guardar_configuracion(df_config)
        st.success("Configuración actualizada.")
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("Descargar Data")
    
    # LÓGICA DE DESCARGA EXCEL MEJORADA
    if os.path.exists(ARCHIVO_DB):
        with open(ARCHIVO_DB, "rb") as f:
            st.sidebar.download_button(
                label="📥 Descargar Base de Datos (EXCEL REAL)",
                data=f,
                file_name="Base_Datos_TEG_Oficial.xlsx", # Nombre más claro
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.sidebar.warning("No hay registros todavía.")

# --- VISTA ESTUDIANTE ---
st.title("Sistema de Inscripciones")

if not abierto_proy and not abierto_teg:
    st.warning("⚠️ No hay procesos de inscripción abiertos actualmente.")
    st.stop()

opciones = []
if abierto_proy: opciones.append("Proyecto")
if abierto_teg: opciones.append("TEG")

tipo_tramite = st.selectbox("Seleccione el trámite:", opciones)
st.info(f"Usted está inscribiendo: **{tipo_tramite}**")
st.markdown("---")

c_prog, c_mod = st.columns(2)
programa = c_prog.selectbox("Programa Académico", [
    "Ingeniería Civil", "Ingeniería Industrial", "Ingeniería Mecánica", 
    "Desarrollo Empresarial", "Enfermería Integral", "Artes Audiovisuales", "Fisioterapia"
])
modalidad = c_mod.radio("Modalidad", ["Individual", "Pareja"])
titulo = st.text_input("Título del Trabajo")
linea = st.text_input("Línea de Investigación")

st.markdown("---")

# --- SECCION AUTOR 1 ---
st.subheader("👤 Datos Autor 1 (Principal)")
col1, col2 = st.columns(2)
a1_nom = col1.text_input("Nombres (Autor 1)")
a1_ced = col2.text_input("Cédula (Autor 1)")
a1_ema = col1.text_input("Correo (Autor 1)")
a1_tlf = col2.text_input("Teléfono (Autor 1)")

st.markdown("**Requisitos Autor 1 (Cargar Imágenes .jpg/.png):**")
f1_pla = st.file_uploader("1. Planilla de Inscripción (A1)", type=['jpg','png','jpeg'], key="f1a")
f1_ced = st.file_uploader("2. Cédula de Identidad (A1)", type=['jpg','png','jpeg'], key="f1b")
f1_com = st.file_uploader("3. Constancia Comunidad (A1)", type=['jpg','png','jpeg'], key="f1c")
f1_ser = st.file_uploader("4. Constancia Servicio Comunitario (A1)", type=['jpg','png','jpeg'], key="f1d")
f1_rec = st.file_uploader("📄 Récord Académico (Solo PDF)", type=['pdf'], key="f1e")

# --- SECCION AUTOR 2 (CONDICIONAL) ---
a2_nom, a2_ced, a2_ema, a2_tlf = "", "", "", ""
f2_pla, f2_ced, f2_com, f2_ser = None, None, None, None

if modalidad == "Pareja":
    st.markdown("---")
    st.subheader("👥 Datos Autor 2")
    col3, col4 = st.columns(2)
    a2_nom = col3.text_input("Nombres (Autor 2)")
    a2_ced = col4.text_input("Cédula (Autor 2)")
    a2_ema = col3.text_input("Correo (Autor 2)")
    a2_tlf = col4.text_input("Teléfono (Autor 2)")
    
    st.markdown("**Requisitos Autor 2 (Cargar Imágenes .jpg/.png):**")
    st.info("Nota: La planilla puede ser la misma del Autor 1, pero cárguela nuevamente aquí.")
    f2_pla = st.file_uploader("1. Planilla de Inscripción (A2)", type=['jpg','png','jpeg'], key="f2a")
    f2_ced = st.file_uploader("2. Cédula de Identidad (A2)", type=['jpg','png','jpeg'], key="f2b")
    f2_com = st.file_uploader("3. Constancia Comunidad (A2)", type=['jpg','png','jpeg'], key="f2c")
    f2_ser = st.file_uploader("4. Constancia Servicio Comunitario (A2)", type=['jpg','png','jpeg'], key="f2d")
    f2_rec = st.file_uploader("📄 Récord Académico A2 (Solo PDF)", type=['pdf'], key="f2e")

st.markdown("---")

# --- SECCION TUTOR ---
st.subheader("🎓 Datos del Tutor y Trabajo")
col_t1, col_t2 = st.columns(2)
t_nom = col_t1.text_input("Nombre del Tutor")
t_ced = col_t2.text_input("Cédula del Tutor")

st.markdown("**Requisitos del Tutor y Trabajo (Imágenes):**")
f_tut_car = st.file_uploader("Carta de Aceptación del Tutor", type=['jpg','png','jpeg'], key="ft1")
f_tut_ced = st.file_uploader("Cédula del Tutor", type=['jpg','png','jpeg'], key="ft2")

f_teg_apto = None
if tipo_tramite == "TEG":
    st.warning("Requisito Adicional TEG:")
    f_teg_apto = st.file_uploader("Carta de Apto para Defensa", type=['jpg','png','jpeg'], key="fteg")

st.markdown("**Documento Final:**")
file_tesis = st.file_uploader("📂 Archivo del Proyecto/TEG (WORD .docx)", type=['docx','doc'])


# --- BOTON DE ENVIO ---
if st.button("Formalizar Inscripción"):
    # Validacion basica
    if not titulo or not a1_ced or not file_tesis:
        st.error("❌ Faltan datos obligatorios (Título, Cédula o Archivo Word).")
    else:
        with st.spinner("Creando expediente digital..."):
            
            # 1. Agrupar imagenes
            imagenes_a_procesar = [f1_pla, f1_ced, f_tut_car, f_tut_ced, f1_com, f1_ser]
            
            if f_teg_apto:
                imagenes_a_procesar.append(f_teg_apto)
                
            if modalidad == "Pareja":
                imagenes_a_procesar.extend([f2_pla, f2_ced, f2_com, f2_ser])
            
            # Generar PDF
            nombre_pdf = f"EXP_{tipo_tramite}_{a1_ced}.pdf"
            ruta_pdf = generar_pdf_expediente(imagenes_a_procesar, nombre_pdf)
            
            if ruta_pdf is None:
                ruta_pdf = "N/A (Sin soportes)"

            # 2. Guardar Word
            nombre_word = f"DOC_{tipo_tramite}_{programa}_{a1_ced}.docx"
            ruta_word_final = os.path.join(CARPETA_TESIS, nombre_word)
            with open(ruta_word_final, "wb") as f:
                f.write(file_tesis.getbuffer())

            # 3. Guardar en BD (EXCEL)
            datos = {
                "FECHA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "PROGRAMA_ACADEMICO": programa,
                "TIPO_TRAMITE": tipo_tramite,
                "MODALIDAD": modalidad,
                "TITULO_PROYECTO": titulo,
                "LINEA_INVESTIGACION": linea,
                "AUTOR1_CEDULA": a1_ced,
                "AUTOR1_NOMBRE": a1_nom,
                "AUTOR1_TLF": a1_tlf,
                "AUTOR1_CORREO": a1_ema,
                "AUTOR2_CEDULA": a2_ced,
                "AUTOR2_NOMBRE": a2_nom,
                "AUTOR2_TLF": a2_tlf,
                "AUTOR2_CORREO": a2_ema,
                "TUTOR_NOMBRE": t_nom,
                "TUTOR_CEDULA": t_ced,
                "RUTA_EXPEDIENTE": ruta_pdf,
                "RUTA_TRABAJO": ruta_word_final
            }
            guardar_en_bd(datos)
            
            # 4. Constancia
            path_constancia = generar_constancia(datos)
            
            st.success("✅ ¡INSCRIPCIÓN COMPLETADA EXITOSAMENTE!")
            with open(path_constancia, "rb") as f:
                st.download_button("📥 Descargar Comprobante de Inscripción", f, "Comprobante.pdf")