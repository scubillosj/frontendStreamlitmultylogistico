import pandas as pd
from datetime import date, datetime
import re

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