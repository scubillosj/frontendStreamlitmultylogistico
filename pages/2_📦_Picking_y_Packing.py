
import sys
import os
# Agrega la carpeta padre (FrontendStreamlit) al PATH.
# Esto permite que Python encuentre el paquete 'procesamiento'.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#Libreria
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
from datetime import datetime
#FUNCIONES PROPIAS
from procesamiento.utils import to_excel_bultos, validation_data, convert_dates_to_iso, to_excel_regueros_por_origen
from procesamiento.utilexport import BultosMasivo2, BultosMasivo, Regerospickingmasivo, RegerosSeleccion

#FUNCIONES DE AUTENTICACIÓN
from auth_logic import protected_post, logout_user, DJANGO_API_BASE
# Constante que usaremos como placeholder en lugar de NaN para la serialización

st.set_page_config(page_title="Picking y Packing", layout="wide") 
st.title("📦 Picking y Packing")

NAN_PLACEHOLDER = "__NAN_PLACEHOLDER__"

DEFAULT_END_DATE = datetime.now().date()

API_CORTE_CREATE = DJANGO_API_BASE + "procesamiento/crear_corte/"  
API_PICKING_UPLOAD = DJANGO_API_BASE + "procesamiento/upload_picking_packing/"

#La libreria streamlit requiere  de la libreria io para generar los formatos de texto
if not st.session_state.get('logged_in'):
    st.error("🔒 Debe iniciar sesión para acceder a esta página.")
    # El CSS oculta el enlace, pero este código impide que el contenido se cargue
    st.stop()

# --- INICIALIZACIÓN DE ESTADO ---
if 'latest_summary' not in st.session_state:
    st.session_state['latest_summary'] = pd.DataFrame()
if 'corte_creado' not in st.session_state:
    st.session_state['corte_creado'] = False
if 'nombre_corte' not in st.session_state:
    st.session_state['nombre_corte'] = None
    

# --- FUNCIONES PARA GENERAR DATOS ---
def to_excel(df):

    """Convierte el DataFrame a un archivo Excel binario."""

    output = BytesIO()

    # Requiere el paquete openpyxl o xlsxwriter

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        df.to_excel(writer, index=False, sheet_name='Resumen_Negados')

    processed_data = output.getvalue()

    return processed_data


def display_summary_report():

    if not st.session_state['latest_summary'].empty:

        st.header("Información del corte")

        st.markdown("Resumen de la información")

        

        df_summary = st.session_state['latest_summary']

       

        col1, col2 = st.columns([1, 1])


                
# --- 1. PREPARAR DATOS CLAVE PARA LOS PDF --- # Si el DF de resumen no está vacío, usamos la primera fila como referencia 
        datos_clave = { "nombre_cliente": df_summary['nombreAsociado'].iloc[0] if 
                         'nombreAsociado' in df_summary.columns else "Cliente Desconocido", 
                         "id_documento": "CARGA-" + pd.Timestamp.now().strftime("%Y%m%d%H%M"), 
                         "vendedor": df_summary['vendedor'].iloc[0] if 'vendedor' in df_summary.columns else "N/A", 
                         "ciudad": df_summary['cuidad'].iloc[0] if 'cuidad' in df_summary.columns else "N/A", 
                         "codigo_zona": df_summary['codigoZona'].iloc[0] if 'codigoZona' in df_summary.columns else "N/A", 
                         "zona": df_summary['zona'].iloc[0] if 'zona' in df_summary.columns else "N/A"
                         }


       
        
        with col1: 
        # --- 2. BOTÓN DE RUTA BULTOS ZONA PDF ---
            dfbultosmasivo= BultosMasivo2(df_summary)
            dfbultosmasivo2 = to_excel_bultos(dfbultosmasivo, "BULTOS POR ZONA")
            st.download_button( 
                    label="Descargar excel bultos zona", 
                    data=dfbultosmasivo2,
                    file_name='resumen_bultoszona.xlsx',
                    mime='application/xlsx', 
                    help='Descarga el resumen en excel del bultos por zona'
                )
            
        with col2: 
        # --- 3. BOTÓN DE RUTA REGUEROS ZONA ---
            dfregueros= RegerosSeleccion(df_summary)
            dfregueros2 = to_excel_regueros_por_origen(dfregueros, "REGUEROS POR ZONA")
            st.download_button( 
                    label="Descargar excel regueros zona", 
                    data=dfregueros2,
                    file_name='resumen_regueroszona.xlsx',
                    mime='application/xlsx', 
                    help='Descarga el resumen en excel del regueros por zona'
                )

     
        
        info1 = df_summary.groupby(["codigoZona"])[["pesoUnitario","nombreAsociado", "origen"]].agg(
        Peso=("pesoUnitario", "sum"),
        Clientes= ("nombreAsociado", "nunique"),
        Ordenes=("origen", "nunique")).reset_index()
        
        info2 = df_summary.groupby(["vendedor"])[["pesoUnitario","nombreAsociado", "origen"]].agg(
        Peso=("pesoUnitario", "sum"),
        Clientes= ("nombreAsociado", "nunique"),
        Ordenes=("origen", "nunique")).reset_index()
        
        st.dataframe(info1, use_container_width=True, hide_index=True)
        st.dataframe(info2, use_container_width=True, hide_index=True)
        
# ----------------------------------------------------------------------

def procesar_picking_packing(api_url):
    """
    Lógica para la carga masiva de picking, visible solo si el corte fue creado.
    """
    
    st.header("2. Ingresar las facturas en borrador")
    st.subheader(f"✅ Listo para cargar. Usando Corte: **{st.session_state['nombre_corte']}**")
    st.caption("el archivo plano no debe contener titulos, verifica que no los tenga")

    uploaded_file = st.file_uploader("Cargar archivo XLSX", type=["xlsx"])

    if uploaded_file:
        # 1. Lectura y preparación para envío
        df_original = pd.read_excel(uploaded_file)
        #Revisión de los errores en datos
        revision_data = validation_data(df_original)
        
        if revision_data is None:
           st.success("Los datos no contienen errores continuar carga")
        else: 
           st.warning(revision_data)
        
        df_para_envio = convert_dates_to_iso(df_original.copy())
        df_para_envio = df_para_envio.replace({np.nan: NAN_PLACEHOLDER})
        data_to_send = df_para_envio.to_dict(orient='records')
        
 
        for record in data_to_send:
            record['nombrecorte'] = st.session_state['corte_id']
        

        if st.button("Procesar Picking y Packing", type="primary"):
            with st.spinner("Generando reportes ...."):
                try:
                    response = protected_post(api_url, data=data_to_send) 
                    
                    if response.status_code == 401:
                         st.error("❌ Sesión expirada o no autorizada.")
                         logout_user() 
                         return
                    
                    response_data = response.json()
                    
                    if response.status_code == 201:
                        # ✅ Aquí SÍ usamos el resumen porque esperamos data masiva
                        st.success(f"✅ Datos guardados. Filas: {response_data.get('filas_guardadas')}")
                        summary_data = response_data.get('resumen_procesado', [])
                        
                        if summary_data:
                            df_summary = pd.DataFrame(summary_data)
                            st.session_state['latest_summary'] = df_summary
                            st.toast("Resumen de carga generado.")
                            st.rerun() # Forzar rerun para mostrar el resumen de los datos

                    elif response.status_code == 400:
                        st.error("❌ Error de validación en Django. Verifique los detalles.")
                        st.json(response_data)
                    else:
                        st.error(f"❌ Error API: {response.status_code}")
                        st.code(response.text)
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Error de conexión. Revisa el servidor.")
                except requests.exceptions.JSONDecodeError:
                    st.error(f"❌ Error API: El servidor devolvió una respuesta no válida ({response.status_code}).")
                    st.code(response.text)





   # ----------------------------------------------------------------------
# --- MAIN ---
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide")
    st.title("📊 Carga y Reporte de corte de Selección y empaque")
    
    # ----------------------------------------------------
    # 1. CREAR CORTE (Bloque Secuencial)
    # ----------------------------------------------------
    st.header("1. Crear corte")
    
    corte_ya_creado = st.session_state['corte_creado']
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # ✅ Bloquea la edición si ya se creó el corte
        fechalabel = st.date_input("Fecha", DEFAULT_END_DATE, disabled=corte_ya_creado)
        fecha_iso = fechalabel.isoformat()
    
    with col2:
        # ✅ Muestra el nombre guardado si existe, y bloquea la edición
        namelabel = st.text_input("Nombre del Nuevo Corte", st.session_state['nombre_corte'] or "", disabled=corte_ya_creado)
    
    # El botón solo se muestra si el corte NO ha sido creado.
    if not corte_ya_creado:
        if st.button("Crear corte", type="primary"):
            if not namelabel:
                st.error("El nombre del corte es obligatorio.")
            else:
                with st.spinner("Creando corte ...."):
                    try:
                        data_to_send = {'fecha': fecha_iso, 'nombre': namelabel}
                        
                        # Usamos el API_CORTE_CREATE para el envío de un solo registro
                        response = protected_post(API_CORTE_CREATE, data=data_to_send) 
                        
                        if response.status_code == 401:
                            logout_user() 
                            return
                        
                        response_data = response.json()
                        
                        if response.status_code == 201:
                            st.success(f"✅ Corte '{namelabel}' creado exitosamente.")
                            
                            # 💡 PASO CLAVE: ALMACENAR ESTADO
                            st.session_state['corte_creado'] = True
                            st.session_state['nombre_corte'] = response_data.get("datos_creados", {}).get("nombre", namelabel)
                            st.session_state['corte_id'] = response_data.get("id_creado")
                            
                            st.balloons()
                            st.rerun() 
                            
                        elif response.status_code == 400:
                            st.error(f"❌ Error de validación: {response_data.get('nombre', ['Error desconocido'])[0]}")
                        else:
                            st.error(f"❌ Error API: {response.status_code}")
                            st.code(response.text)
                            
                    except requests.exceptions.RequestException:
                        st.error("❌ Error de conexión. Revisa el servidor.")
                    except requests.exceptions.JSONDecodeError:
                        st.error(f"❌ Error API: El servidor devolvió una respuesta no válida ({response.status_code}).")
                        st.code(response.text) 

    # ----------------------------------------------------
    # 2. PROCESAR PICKING Y PACKING 
    # ----------------------------------------------------
    
    if corte_ya_creado:
        procesar_picking_packing(API_PICKING_UPLOAD)
    else:
        st.info("👆 Complete el Paso 1 (Crear corte) para habilitar la sección de carga masiva.")

    display_summary_report()


if __name__ == '__main__':
    main()