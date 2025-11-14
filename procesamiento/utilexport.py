import pandas as pd
import re
import numpy as np
from typing import Dict, Any


'''
esto debe ser un EXCEL
'''

def rutaPesodf (df_crudo: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")
    
    df_limpio = df_crudo.copy()
    df_limpio = df_limpio.dropna(subset=["Nombre de la empresa a mostrar en la factura"])
    
    df_rutapeso = df_limpio.groupby(
        by=["Asociado/Ciudad", "Asociado/Zona", "Nombre de la empresa a mostrar en la factura", 
            "Vendedor", "Origen", "ID"]
    )["Peso Total"].sum().reset_index()
    
    return df_rutapeso


def transformacionPicking (df_crudo: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")

    # Copia de seguridad para no modificar el DataFrame original (si aplica)
    pickzona = df_crudo.copy()
    
    def extract_number(text):
        match = re.search(r"\((\d+)\)", str(text))
        if match:
          return int(match.group(1))
        else:
          return 1
      
    # Aplicar la función
    pickzona["Unidadesxpaca"] = pickzona["producto"].apply(extract_number)
    
    # Create columna de pacas
    pickzona["paca"] = np.where(
       pickzona["cantidad"] >= pickzona["Unidadesxpaca"],
       pickzona["cantidad"] // pickzona["Unidadesxpaca"],
    0,
    )

    pickzona["unidades"] = np.where(
        pickzona["cantidad"] < pickzona["Unidadesxpaca"],
        pickzona["cantidad"],
        pickzona["cantidad"] % pickzona["Unidadesxpaca"],
        )  
    
    return pickzona

#Es una función que agrupa todo lo que se esta pidiendo
def listadoTotal (df_crudo: pd.DataFrame) -> pd.DataFrame:
     
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")

    # Copia de seguridad para no modificar el DataFrame original (si aplica)
    #A todos se les aplica la función de transformación
    pickzona = df_crudo.copy()
    pickzona = transformacionPicking(pickzona)
    
    pickzona["codigoZona"] = pickzona["codigoZona"].fillna("Otras Zonas")  # Fill None values with empty string
    listadototal = pickzona.groupby(["marca", "producto"])[
         ["cantidad", "paca", "unidades", "origen", "codigoZona"]
    ].agg(
       Unidades_pedidas=("cantidad", "sum"),
       Pacas=("paca", "sum"),
       Unidades_faltantes=("unidades", "sum"),
       Origen=("origen", lambda x: ", ".join(x.unique())),
       Zona=("codigoZona", lambda x: ", ".join(x.unique())),
    ).reset_index()
    
    return listadototal


def BultosMasivo (df_crudo: pd.DataFrame) -> pd.DataFrame:
     
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")
    #A todos se les aplica la función de transformación
    pickzona = df_crudo.copy()
    pickbultos = transformacionPicking(pickzona)

    filtro_bultos = pickbultos["paca"] > 0
    pickbultos = pickbultos[filtro_bultos]
    Bultos_pickingmasivo = pickbultos.groupby(
        ["marca", "producto"]
    )[["paca", "codigoZona","origen"]].agg(
        Pacas=("paca", "sum"),
        codigoZona= ("codigoZona", lambda x: ", ".join(x.unique())),
        Origen=("origen", lambda x: ", ".join(x.unique()))).reset_index()
    
    return Bultos_pickingmasivo

def BultosMasivo2 (df_crudo: pd.DataFrame) -> pd.DataFrame:
     
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")
    #A todos se les aplica la función de transformación
    pickzona = df_crudo.copy()
    pickbultos = transformacionPicking(pickzona)

    filtro_bultos = pickbultos["paca"] > 0
    pickbultos = pickbultos[filtro_bultos]
    Bultos_pickingmasivo = pickbultos.groupby(
        ["codigoZona","marca", "producto"]
    )[["paca","origen"]].agg(
        Pacas=("paca", "sum"),
        Origen=("origen", lambda x: ", ".join(x.unique()))).reset_index()
    
    return Bultos_pickingmasivo



def Regerospickingmasivo (df_crudo: pd.DataFrame) -> pd.DataFrame:
     
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")
    # Copia de seguridad para no modificar el DataFrame original (si aplica)
    #A todos se les aplica la función de transformación
    pickzona = df_crudo.copy()
    pickregerosm = transformacionPicking(pickzona)
    filtro_pickregerosm = pickregerosm["unidades"] > 0
    pickregerosm = pickregerosm[filtro_pickregerosm]
    Regeros_pickingmasivo = pickregerosm.groupby(["marca", "producto"])[
          ["unidades","codigoZona", "origen"]
    ].agg(
          unidades=("unidades", "sum"),
          codigoZona= ("codigoZona", lambda x: ", ".join(x.unique())),
          Origen=("origen", lambda x: ", ".join(x.unique()))).reset_index()
    
    return Regeros_pickingmasivo


#La respuesta de este es un diccionario con datos(Se divide por zona)
def RegerosSeleccion(df_crudo: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")

    pickzona = df_crudo.copy()
    
    # 1. APLICAR TRANSFORMACIÓN Y FILTRADO
    pickregeros = transformacionPicking(pickzona)
    
    # Aplicar el filtro después de la transformación
    filtro_r = pickregeros["unidades"] > 0
    df_filtrado = pickregeros[filtro_r]
    
    # 2. AGRUPACIÓN Y AGREGACIÓN
    df_regueros = df_filtrado.groupby(
        by=["codigoZona", "zona", "origen", "marca","producto"]
    ).agg(
        Unidades_faltantes=("unidades", "sum")
    ).reset_index() 
        
    return df_regueros
   
    



"""
Falta analizar los conductores
    # agrupador zona x producto, unidades, unidadesxpaca, paca, origen
    conductorbultos = pickzona.copy()
    filtro_r = conductorbultos["paca"] > 0
    conductorbultos = conductorbultos[filtro_r]
    pickingconductor = conductorbultos.groupby(
          ["Cod zona", "zona", "Origen", "Líneas de factura/Producto"]
    )[["Líneas de factura/Cantidad", "paca", "unidades", "Origen"]].agg(
    # Unidades_pedidas=('Líneas de factura/Cantidad', 'sum'),
          Pacas=("paca", "sum")
    # Unidades_faltantes=('unidades', 'sum')
    # Origen=('Origen', lambda x: ', '.join(x.unique()))
    )

# 6. Documento Crear el ExcelWriter
    writer = pd.ExcelWriter("Conductores bultos.xlsx", engine="xlsxwriter")

# hacer el agrupador de zones
    zones = pickzona["Cod zona"].unique()

# Iteración de zonas
    for zone in zones:
    # Ingresar datos
        zone_data = pickingconductor.loc[
             pickingconductor.index.get_level_values("Cod zona") == zone]

    # Ingresar nombre
    zone_data.to_excel(
        writer, sheet_name=str(zone)
    )  # Convert zone to string for sheet name

    # Save the Excel file
    writer.close()


"""