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
import json
import plotly.express as px
#FUNCIONES PROPIAS
from procesamiento.utils import convert_dates_to_iso, to_excel, pickingPacking, to_excel_agrupado
from procesamiento.utilexport import rutaPesodf, BultosMasivoConductores
#FUNCIONES DE AUTENTICACIÓN
from auth_logic import logout_user

st.set_page_config(page_title="Ruta y Peso", layout="wide") 
st.title("🚗 Conductores")

#La libreria streamlit requiere  de la libreria io para generar los formatos de texto
if not st.session_state.get('logged_in'):
    st.error("🔒 Debe iniciar sesión para acceder a esta página.")
    # El CSS oculta el enlace, pero este código impide que el contenido se cargue
    st.stop()

def dividir_zona(zona):

    if pd.isna(zona):  # Maneja valores NaN (Not a Number) o None si los hubiera
        return [None, None]
    try:
        partes = str(zona).split(".", 1)  # Divide solo por el primer punto
        if len(partes) == 1:
            return [
                partes[0],
                None,
            ]  # Si no hay punto, 'Cod zona' es la zona, 'zona' es None
        else:
            return partes
    except:
        return [None, None] 

def display_summary_report(df_crudo: pd.DataFrame):

        st.markdown("Resumen de la información")
        
        df_crudo[["Cod zona", "zona"]] = (
        df_crudo["Asociado/Zona"]
        .apply(dividir_zona)
        .apply(pd.Series)
    )
        df_agrupadocod = df_crudo.groupby(["Cod zona"]).agg(
        Peso = ("Peso Total", "sum"),
        Clientes = ("Nombre de la empresa a mostrar en la factura", "nunique")
        ).reset_index()
    
        df_agrupado = df_crudo.groupby(["Cod zona", "zona"]).agg(
        Peso = ("Peso Total", "sum"),
        Clientes = ("Nombre de la empresa a mostrar en la factura", "nunique")
        ).reset_index()
        
        st.markdown("Agrupación por codigo de zona")
        st.dataframe(df_agrupadocod, use_container_width=True, hide_index=True)
        st.markdown("Agrupación por zona")
        st.dataframe(df_agrupado, use_container_width=True, hide_index=True)
        
       

      
# ----------------------------------------------------------------------

#Esta función es para guardar datos y no se pierda en los otros procesos

if 'latest_summary' not in st.session_state:

    st.session_state['latest_summary'] = pd.DataFrame()

   

def main():

  st.set_page_config(layout="wide")

  st.title("📊 Carga y Reporte de agrupación conductores")

  st.header("Ingresar todas las ordenes a procesar")

  st.subheader("Recuerda que debes exportar PYTHON CONDUCTORES")

  st.caption("el archivo no debe contener titulos ni agrupaciones,verificar que no los tenga")


  #Carga de datos
  uploaded_file = st.file_uploader("Cargar archivo XLSX", type=["xlsx"])

  if uploaded_file:
    # 1. Lectura y preparación para envío
    df_original = pd.read_excel(uploaded_file)
    #Las bases de datos estandarizan la forma de utilizar los formatos fecha
    df_para_envio = convert_dates_to_iso(df_original.copy())
    
    #Trasnformación de datos para visualización
    df_zonapeso = rutaPesodf(df_para_envio)
    # PASO CLAVE: Renombrar las columnas una vez
    df_bultos_renombrado = pickingPacking(df_para_envio) 

    # PASO CLAVE: Aplicar la lógica de bultos al DataFrame YA RENOMBRADO
    df_bultos = BultosMasivoConductores(df_bultos_renombrado)
    
    total_clientes = df_zonapeso['Nombre de la empresa a mostrar en la factura'].nunique()
    total_peso = df_zonapeso['Peso Total'].sum()
    
    st.header("Resumen del Conductor")
    
    col1, col2  = st.columns([1, 1])
    
    with col1:
        with col1:
          st.metric(
        label="Total Clientes", 
        value=total_clientes, 
        delta="Nuevo KPI" 
         )
    with col2:
        with col1:
          st.metric(
        label="Total Peso", 
        value=total_peso, 
        delta="Nuevo KPI" 
         )
    
        
    st.dataframe(df_zonapeso, use_container_width=True, hide_index=True)
    
    col3, col4, col5  = st.columns([1, 1, 1])
    with col3: 
         if st.button("Generar estadisticas", type="primary"):
          with st.spinner("Generando reportes ...."):
            display_summary_report(df_zonapeso)
    with col4:
     df_zonapeso2 = to_excel(df_zonapeso, "REPORTE ZONA PESO")
     st.download_button( 
                    label="Descargar Resumen a Excel", 
                    data=df_zonapeso2,
                    file_name='resumen_rutapeso.xlsx',
                    mime='application/xlsx', 
                    help='Descarga el resumen en excel del zona peso'
                )
    with col5:
     df_bultos2 = to_excel_agrupado(df_bultos, "REPORTE CONDUCTORES")
     st.download_button( 
                    label="Descargar Resumen Conductor", 
                    data=df_bultos2,
                    file_name='resumen_conductor.xlsx',
                    mime='application/xlsx', 
                    help='Descarga el resumen en excel del conductores'
                )
    
   
       
   



if __name__ == '__main__':

    main()