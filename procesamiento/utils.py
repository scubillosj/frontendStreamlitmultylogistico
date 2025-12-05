import pandas as pd
from datetime import date, datetime
from io import BytesIO
import re
from typing import Optional 
import numpy as np 

MARCA_MAP = {
    "32": "ADORE",
    "25": "AGRALBA-IVANAGRO",
    "46": "AMALIAS",
    "20": "BIOS",
    "14": "CANAMOR",
    "44": "CIPA",
    "18": "CONTEGRAL GRANDES ESPECIES",
    "19": "FINCA GRANDES ESPECIES",
    "21": "GABRICA",
    "24": "ITALCOL",
    "23": "ITALCOL GRANDES ESPECIES",
    "27": "JAULAS",
    "29": "KITTY PAW",
    "30": "LABORATORIOS ZOO",
    "36": "MAXIPETS",
    "45": "MONAMI",
    "47": "FINOTRATO",
    "26": "NUTRA NUGGETS",
    "38": "PINOMININO",
    "12": "POLAR",
    "00": "PUNTO DE VENTA-OTROS",
    "02": "PUNTO DE VENTA-OTROS",
    "1": "PUNTO DE VENTA-OTROS",
    "15": "PUNTO DE VENTA-OTROS",
    "17": "PUNTO DE VENTA-OTROS",
    "28": "PUNTO DE VENTA-OTROS",
    "35": "PUNTO DE VENTA-OTROS",
    "39": "PUNTO DE VENTA-OTROS",
    "CR": "PUNTO DE VENTA-OTROS",
    "10": "PUNTOMERCA",
    "37": "PANDAPAN",
    "40": "PURINA",
    "41": "SEMILLAS",
    "42": "SOLLA",
    "43": "SOLLA MASCOTAS",
    "34": "TETRACOLOR",
}


def json_serial_default(obj):
    """
    Función de ayuda para la serialización JSON.
    Convierte cualquier objeto date, datetime o Timestamp a formato ISO 8601.
    """
    # Maneja objetos de fecha y hora nativos de Python
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    
    # Maneja objetos Timestamp de Pandas (aunque Pandas debería manejarlos en el to_dict)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()

    # Si no es fecha, lanza el error predeterminado
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

############ Código de producto negado - para importación masiva #######################################

def limpiar_y_preparar_detalle(data_or_path) -> pd.DataFrame:
    """
    Limpia y transforma los datos recibidos desde admin (Dataset) o DataFrame.
    """
    if isinstance(data_or_path, pd.DataFrame):
        data = data_or_path.copy()
    else:
        # Intentamos convertir Dataset a DataFrame
        try:
            data = pd.DataFrame(data_or_path.dict)
        except AttributeError:
            # Si no es Dataset ni DataFrame, asumimos que es path
            data = pd.read_excel(data_or_path)

    # Rellenar valores faltantes
    data = data.fillna(method="ffill").fillna(method="bfill")

    # Fecha normalizada
    if "Fecha Programada" in data.columns:
        data["Fecha"] = pd.to_datetime(
            data["Fecha Programada"], errors="coerce"
        ).dt.date
    else:
        # Si no hay columna, poner fecha de hoy
        data["Fecha"] = pd.Timestamp.today().date()

    # Calcular producto negado
    data["Producto negado"] = data.get(
        "Movimientos de Existencias/Cantidad Real", 0
    ) - data.get("Movimientos de Existencias/Cantidad Reservada", 0)

    # Extraer marca
    if "Movimientos de Existencias/Descripción" in data.columns:
        data["marca"] = data["Movimientos de Existencias/Descripción"].str.slice(1, 3)
        data["marca"] = data["marca"].replace(MARCA_MAP)
    else:
        data["marca"] = "OTROS"

    # Filas necesarias para guardar
    detalle = data[
        [
            "Fecha",
            "Movimientos de Existencias/Descripción",
            "Producto negado",
            "marca",
            "Documento Origen",
            "Referencia",
        ]
    ].copy()

    detalle = detalle.rename(
        columns={
            "Fecha": "fecha",
            "Movimientos de Existencias/Descripción": "producto",
            "Producto negado": "cantidad_negada",
            "Documento Origen": "origen",
            "Referencia": "referencia",
        }
    )

    # Filtramos solo los registros con cantidad_negada > 0
    detalle = detalle[detalle["cantidad_negada"] > 0]

    return detalle


def convert_dates_to_iso(df):
    """Convierte columnas de fecha de Pandas a formato string ISO 8601."""
    # ... (El código de esta función permanece igual, ya que solo limpia columnas detectadas) ...
    df_copy = df.copy()
    date_types = ['datetime64', 'datetime64[ns]', 'datetimetz']
    
    for col in df_copy.select_dtypes(include=date_types).columns:
        df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
        df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d')
        
    return df_copy

def validation_data(df) -> str | None:
    df = df.copy()
    listado_origen = df['Origen'].unique()
    
    for origen in listado_origen:
       if len(str(origen)) > 7:
        return "Revisar los origenes alguno de estos pueden estar malos"
    
    


def to_excel(df, base_titulo=str): # Nota: base_titulo=str es un patrón inusual para un valor por defecto.
    """
    Convierte el DataFrame a un archivo Excel binario, ajustando el ancho,
    añadiendo bordes, colocando un título general con la fecha del sistema,
    y manejando correctamente los valores NaN.
    """
    
    # --- LÓGICA DE FECHA ---
    fecha_actual = datetime.now()
    fecha_formateada = fecha_actual.strftime("%Y-%m-%d") 
    titulo_completo = f"{base_titulo} (Generado el: {fecha_formateada})"
    
    # --- LÓGICA DE EXCEL ---
    output = BytesIO()
    sheet_name = 'ReportesS'
    startrow_data = 1 
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # Escribir el DF. startrow=1 para dejar la Fila 0 libre para el título
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=startrow_data)
        
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        num_rows, num_cols = df.shape
        
        # --- DEFINICIÓN DE FORMATOS ---
        
        # Formato para el TÍTULO GENERAL (Fila 0)
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#D9D9D9', # Color de fondo gris claro
            'border': 1
        })
        
        # Formato para los ENCABEZADOS DE COLUMNA (Fila 1)
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'border': 1 
        })
        
        # Formato para los DATOS (Fila 2 en adelante)
        data_format = workbook.add_format({
            'border': 1 
        })
        
        # --- APLICAR TÍTULO Y FORMATOS ---

        # 1. Insertar y fusionar el TÍTULO GENERAL (Fila 0) con la fecha
        worksheet.merge_range(0, 0, 0, num_cols - 1, titulo_completo, title_format)

        # 2. Aplicar el formato a los ENCABEZADOS DE COLUMNA (Fila 1)
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(startrow_data, col_num, value, header_format)

        # 3. Aplicar el formato de borde a las celdas de DATOS
        for row_num in range(startrow_data + 1, num_rows + startrow_data + 1):
            for col_num in range(num_cols):
                cell_value = df.iloc[row_num - startrow_data - 1, col_num] 
                
                # VERIFICACIÓN Y MANEJO DE NaN (SOLUCIÓN AL TypeError)
                if pd.isna(cell_value):
                    # Si es NaN o None, escribimos una cadena vacía con write_string
                    worksheet.write_string(row_num, col_num, '', data_format)
                else:
                    # Si contiene datos, usamos la función write() general
                    worksheet.write(row_num, col_num, cell_value, data_format)
        
        # 4. Ajustar el ancho de las columnas
        for i, col in enumerate(df.columns):
            # Asegurar que el cálculo de longitud maneja los nulos convirtiéndolos a str
            max_data_length = df[col].astype(str).str.len().max()
            header_length = len(col)
            max_length = max(header_length, max_data_length or 0) + 3 
            worksheet.set_column(i, i, max_length)

    processed_data = output.getvalue()
    return processed_data
    
    
############ Código de picking and packing #######################################

############ Transformaciones ##############

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
        return [None, None]  # En caso de cualquier otro error, devuelve [None, None]

#### Esta función me permite completar datos nulos en zona
def zona_blanco(row):
    # Verificar si 'codigoZona' es nulo o igual al string 'nan'
    if pd.isna(row["codigoZona"]) or str(row["codigoZona"]).lower() == "nan":
        row["codigoZona"] = row["cuidad"]
    # Verificar si 'zona' es nulo o igual al string 'nan'
    if pd.isna(row["zona"]) or str(row["zona"]).lower() == "nan":
        row["zona"] = row["cuidad"]
    return row


# --- Constantes ---
# Este diccionario DEBE estar fuera de la función.
COLUMNAS_FINALES_MAPEO = {
    # Claves SIN tildes (gracias a quitar_tildes) : Valores (Nombres del Modelo de Django)
    "Nombre de la empresa a mostrar en la factura": "nombreAsociado",
    "Fecha de Factura/Recibo": "fechaFactura",
    "Asociado/Documento de Identificación": "identificacionAsociado",
    "Vendedor": "vendedor",
    "Líneas de factura/Cantidad": "cantidad",
    "Líneas de factura/Producto": "producto",
    "Líneas de factura/Producto/Peso": "pesoUnitario",
    "Asociado/Ciudad": "cuidad", 
    "Asociado/Zona": "zonaAsociadoOriginal", 
    "Origen": "origen",
    "ID": "idOdoo",
    "Términos y condiciones": "conductor", 
    
}

MARCA_MAP = {
    "32": "ADORE",
    "25": "AGRALBA-IVANAGRO",
    "46": "AMALIAS",
    "20": "BIOS",
    "14": "CANAMOR",
    "44": "CIPA",
    "18": "CONTEGRAL GRANDES ESPECIES",
    "19": "FINCA GRANDES ESPECIES",
    "21": "GABRICA",
    "24": "ITALCOL",
    "23": "ITALCOL GRANDES ESPECIES",
    "27": "JAULAS",
    "29": "KITTY PAW",
    "30": "LABORATORIOS ZOO",
    "36": "MAXIPETS",
    "45": "MONAMI",
    "47": "FINOTRATO",
    "26": "NUTRA NUGGETS",
    "38": "PINOMININO",
    "12": "POLAR",
    "00": "PUNTO DE VENTA-OTROS",
    "02": "PUNTO DE VENTA-OTROS",
    "1": "PUNTO DE VENTA-OTROS",
    "15": "PUNTO DE VENTA-OTROS",
    "17": "PUNTO DE VENTA-OTROS",
    "28": "PUNTO DE VENTA-OTROS",
    "35": "PUNTO DE VENTA-OTROS",
    "39": "PUNTO DE VENTA-OTROS",
    "CR": "PUNTO DE VENTA-OTROS",
    "10": "PUNTOMERCA",
    "37": "PANDAPAN",
    "40": "PURINA",
    "41": "SEMILLAS",
    "42": "SOLLA",
    "43": "SOLLA MASCOTAS",
    "34": "TETRACOLOR",
}


# --------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# --------------------------------------------------------------------------

def pickingPacking(df) -> pd.DataFrame:
    """Limpia y transforma los datos, estandarizando nombres de columnas para Django."""
    

    pickzona = df.copy()

 
    # 3. Renombrado y Selección
    # ----------------------------------------------------
    # Renombra el DF usando el mapeo (Nombres limpios -> Nombres del Modelo)
    pickzona.rename(columns=COLUMNAS_FINALES_MAPEO, inplace=True)

    # ----------------------------------------------------
    # 4. Lógica de Transformación
    # ----------------------------------------------------
    
    # Crea las nuevas columnas temporales ('Cod zona' y 'zona')
    # Nota: El nombre 'zonaAsociadoOriginal' es el renombrado final de 'asociado_zona'
    pickzona[["Cod zona", "zona"]] = (
        pickzona["zonaAsociadoOriginal"]
        .apply(dividir_zona)
        .apply(pd.Series)
    )

    # Renombra 'Cod zona' a 'codigoZona' (¡Fija el KeyError de 'Cod zona'!)
    pickzona.rename(columns={"Cod zona": "codigoZona"}, inplace=True)

    # El campo 'zonaAsociadoOriginal' ya no es necesario
    del pickzona["zonaAsociadoOriginal"]

    # Aplicar la función de relleno de zona
    # (Asume que zona_blanco usa los nombres finales 'codigoZona' y 'cuidad')
    pickzona = pickzona.apply(zona_blanco, axis=1)

    # Rellenar valores faltantes (usando el método moderno)
    pickzona = pickzona.ffill()

    # Extraer marca
    if "producto" in pickzona.columns:
        pickzona["marca"] = pickzona["producto"].str.slice(1, 3)
        pickzona["marca"] = pickzona["marca"].replace(MARCA_MAP)
        
    else:
        pickzona["marca"] = "OTROS"
        
    # ----------------------------------------------------
    # 5. Selección Final y Orden del Modelo
    # ----------------------------------------------------
    
    # Esta es la lista FINAL de campos que espera tu modelo de Django
    columnas_modelo_final_orden = [
        "nombreAsociado", "fechaFactura", "identificacionAsociado", "vendedor",
        "cantidad", "producto", "pesoUnitario", "cuidad", 
        "codigoZona", "zona", "origen", "marca", "idOdoo", "conductor" 
    ]
    
    pickzona = pickzona[columnas_modelo_final_orden]
    
    return pickzona



def to_excel_agrupado(df, base_titulo: Optional[str] = "REPORTE"):
    """
    Convierte el DataFrame (asumiendo MultiIndex con 'conductor' en primer nivel) 
    a un archivo Excel, generando una hoja por cada conductor y fusionando las 
    celdas restantes para el agrupamiento visual.
    """
    
    # --- 1. PREPARACIÓN DE DATOS ---
    df_to_write = df.copy()
    
    # Aseguramos que el DF esté plano
    if isinstance(df_to_write.index, pd.MultiIndex):
        index_names = list(df_to_write.index.names)
        df_to_write = df_to_write.reset_index()
    else:
        # Si ya está plano, asumimos que 'conductor' es la primera columna.
        index_names = df_to_write.columns.tolist() 

    # Asumimos que 'conductor' es la primera columna para la separación de hojas
    CONDUCTOR_COL = index_names[0]
    
    # Columnas que serán fusionadas dentro de cada hoja
    MERGE_COLS = index_names[1:] 
        
    # --- LÓGICA DE FECHA ---
    fecha_actual = datetime.now()
    fecha_formateada = fecha_actual.strftime("%Y-%m-%d") 
    
    # --- LÓGICA DE EXCEL MULTI-HOJA ---
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        workbook = writer.book
        
        # --- DEFINICIÓN DE FORMATOS (Una vez) ---
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
            'fg_color': '#D9D9D9', 'border': 1
        })
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 'border': 1 
        })
        data_format = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'top'
        })
        
        # 2. ITERAR SOBRE CADA CONDUCTOR Y CREAR UNA HOJA
        for conductor, df_group in df_to_write.groupby(CONDUCTOR_COL):
            
            # Limpiar el nombre del conductor para usarlo como nombre de hoja
            sheet_name = str(conductor).replace('/', '-').replace(':', '')[:31] # Max 31 chars
            worksheet = workbook.add_worksheet(sheet_name)
            
            # Definir dimensiones y títulos para esta hoja
            num_rows, num_cols = df_group.shape
            startrow_data = 1 
            titulo_completo = f"{base_titulo} - CONDUCTOR: {conductor} (Generado el: {fecha_formateada})"
            
            # Obtenemos los índices de las columnas que SÍ van en la hoja (todas menos 'conductor')
            cols_to_keep = [col for col in df_group.columns if col != CONDUCTOR_COL]
            df_sheet = df_group[cols_to_keep].reset_index(drop=True)
            num_cols_sheet = df_sheet.shape[1]

            # 1. Insertar y fusionar el TÍTULO GENERAL (Fila 0)
            worksheet.merge_range(0, 0, 0, num_cols_sheet - 1, titulo_completo, title_format)

            # 2. Aplicar el formato a los ENCABEZADOS DE COLUMNA (Fila 1)
            for col_num, value in enumerate(df_sheet.columns.values):
                worksheet.write(startrow_data, col_num, value, header_format)
            
            # --- ESCRITURA DE DATOS Y FUSIÓN DE CELDAS ---
            
            # Identificar los índices de las columnas que deben ser fusionadas en esta hoja
            merged_col_indices = {col: df_sheet.columns.get_loc(col) for col in MERGE_COLS}
            data_col_indices = [
                i for i, col in enumerate(df_sheet.columns) if col not in MERGE_COLS
            ]
            
            # A) PROCESAR COLUMNAS DE AGRUPACIÓN (FUSIÓN)
            for col_name, col_index in merged_col_indices.items():
                col_data = df_sheet[col_name]
                current_start_row_df_index = 0
                num_rows_sheet = df_sheet.shape[0]

                for i in range(1, num_rows_sheet + 1):
                    is_end_of_df = (i == num_rows_sheet)
                    
                    val_current = col_data.iloc[i] if i < num_rows_sheet else None
                    val_previous = col_data.iloc[i-1]
                    
                    is_new_group = not is_end_of_df and not pd.isna(val_current) and val_current != val_previous
                    
                    if is_end_of_df or is_new_group:
                        
                        end_row_df_index = i - 1
                        
                        if current_start_row_df_index <= end_row_df_index:
                            
                            excel_start_row = startrow_data + 1 + current_start_row_df_index
                            excel_end_row = startrow_data + 1 + end_row_df_index
                            value = col_data.iloc[current_start_row_df_index]

                            if excel_start_row < excel_end_row:
                                # 1. FUSIONAR CELDA
                                worksheet.merge_range(
                                    excel_start_row, col_index, excel_end_row, col_index, 
                                    value, data_format 
                                )
                            else:
                                # 2. Escribir celda normal (grupo de una sola fila)
                                worksheet.write(excel_start_row, col_index, value, data_format)

                        current_start_row_df_index = i

            # B) PROCESAR COLUMNAS DE DATOS (ESCRITURA NORMAL)
            for i in range(num_rows_sheet):
                excel_row = startrow_data + 1 + i
                for col_index in data_col_indices:
                    cell_value = df_sheet.iloc[i, col_index]
                    
                    # Manejo de NaN/None
                    if pd.isna(cell_value):
                        worksheet.write_string(excel_row, col_index, '', data_format)
                    else:
                        worksheet.write(excel_row, col_index, cell_value, data_format)

            # 4. Ajustar el ancho de las columnas (solo las columnas de esta hoja)
            for i, col in enumerate(df_sheet.columns):
                max_data_length = df_sheet[col].astype(str).str.len().max()
                header_length = len(col)
                max_length = max(header_length, max_data_length or 0) + 3 
                worksheet.set_column(i, i, max_length)

    processed_data = output.getvalue()
    return processed_data