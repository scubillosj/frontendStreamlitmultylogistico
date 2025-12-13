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

def categorize_conductor(conductor):
    conductor = str(conductor).lower()
    if 'transportadora' in conductor:
        return 'TRANSPORTADORA'
    elif 'santiago' in conductor:
        return 'SANTIAGO'
    elif 'edgar' in conductor:
        return 'EDGAR'
    elif 'david' in conductor:
        return 'DAVID'
    elif 'jesus' in conductor:
        return 'DARIO'
    elif 'dario' in conductor:
        return 'DARIO'
    elif 'peligro' in conductor:
        return 'PELIGRO'
    elif 'fabio' in conductor:
        return 'FABIO'
    elif 'stiven' in conductor:
        return 'DAVID'
    elif 'transportadora' in conductor:
        return 'TRANSPORTADORA'
    elif 'agencia' in conductor:
        return 'AGENCIAS'
    elif 'fernando' in conductor:
        return 'FERNANDO'
    else:
        return ''

def BultosMasivoConductores (df_crudo: pd.DataFrame) -> pd.DataFrame:
    
    if not isinstance(df_crudo, pd.DataFrame):
        raise TypeError("La función espera un objeto pd.DataFrame como entrada.")
        
    pickzona = df_crudo.copy()
    # pickbultos debe ser el resultado de la función de transformación
    # asumiendo que ya tiene las columnas 'paca', 'codigoZona', 'zona', 'origen', 'producto', y 'conductor'.
    pickbultos = transformacionPicking(pickzona)
    
    pickbultos['conductor'] = pickbultos['conductor'].apply(categorize_conductor)
    

    # --- CLAVES DE AGRUPACIÓN ACTUALIZADAS ---
    CLAVES_AGRUPACION = ["conductor", "codigoZona", "zona", "origen", "producto"]
    # ----------------------------------------
    

    # 1. Agrupar TODAS las combinaciones de producto/origen.
    df_agrupado_productos = pickbultos.groupby(
        CLAVES_AGRUPACION # <-- Usando las nuevas claves
    )[["paca"]].agg(
        Pacas=("paca", "sum")
    ).reset_index() 

    
    # 2. Identificar qué orígenes tienen CERO pacas en total (por origen, NO por conductor)
    #    Mantenemos la lógica de origen para saber qué origen poner "No lleva bultos"
    total_pacas_por_origen = df_agrupado_productos.groupby('origen')['Pacas'].sum()
    origenes_sin_bultos = total_pacas_por_origen[total_pacas_por_origen == 0].index.tolist()
    origenes_con_bultos = total_pacas_por_origen[total_pacas_por_origen > 0].index.tolist()


    # 3. Filtrar el reporte principal: solo filas donde Pacas > 0
    reporte_principal = df_agrupado_productos[
        df_agrupado_productos['origen'].isin(origenes_con_bultos) & 
        (df_agrupado_productos['Pacas'] > 0)
    ]


    # 4. Crear el DataFrame de excepción para los orígenes sin bultos
    if origenes_sin_bultos:
        # Obtener las claves de agrupación (incluyendo el conductor) para esos orígenes
        df_cero_bultos_base = pickbultos[
            pickbultos['origen'].isin(origenes_sin_bultos)
        ][["conductor", "codigoZona", "zona", "origen"]].drop_duplicates()

        # Añadir las columnas de producto y pacas con los valores de excepción
        df_cero_bultos_base['producto'] = 'No lleva bultos'
        df_cero_bultos_base['Pacas'] = 0
        
        # 5. Combinar los dos reportes
        df_final = pd.concat([reporte_principal, df_cero_bultos_base], ignore_index=True)
    else:
        df_final = reporte_principal
        
    # 6. Ordenar el resultado para la agrupación visual en Excel
    df_final = df_final.sort_values(by=CLAVES_AGRUPACION)
    
    # 7. Convertir de nuevo a MultiIndex (REQUERIDO por to_excel_con_fusion para la fusión)
    # El orden aquí dicta el orden de la fusión en Excel (primero conductor, luego zona, etc.)
    df_final = df_final.set_index(CLAVES_AGRUPACION)
    
    return df_final

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
        Unidades=("unidades", "sum")
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
