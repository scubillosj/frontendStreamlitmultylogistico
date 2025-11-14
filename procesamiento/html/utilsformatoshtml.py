# procesamiento/utilformatos.py
import pandas as pd
from xhtml2pdf import pisa
from io import BytesIO
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- CONFIGURACIÓN DE RUTAS ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicializamos Jinja2 con la función de autoescape importada
JINJA_ENV = Environment(
    loader=FileSystemLoader(CURRENT_DIR),
    autoescape=select_autoescape(['html']) 
)
PRODUCTONEGADO_FILE= 'producto_negado.html'
LISTADO_TEMPLATE_FILE = 'listado_total_table.html'
BULTOS_MASIVO_FILE = 'bultos_masivo2.html'
REGUEROS_ZONA_FILE = 'regueros_zona.html'
LISTADO_TEMPLATE_PICKMASIVO = 'pickingmasivo.html'


def render_to_pdf(html_content: str) -> bytes:
    """Convierte una cadena HTML en un archivo PDF binario (bytes)."""
    
    result_file = BytesIO()

    # La función pisa.pisaDocument hace la conversión
    pisa_status = pisa.pisaDocument(
        src=BytesIO(html_content.encode("utf-8")), 
        dest=result_file                              
    )

    if not pisa_status.err:
        return result_file.getvalue()
    
    # Manejo de error si la generación falla
    print(f"XHTML2PDF ERROR: {pisa_status.err}")
    return None 

def transformacion_pdf_listado(df_listado: pd.DataFrame, datos_clave: dict = None) -> bytes:
    """
    Convierte el DataFrame de Listado Total en un PDF binario con columnas ajustadas visualmente.
    """

    # 1️⃣ Renombrar columnas
    df_reporte = df_listado.rename(columns={
        'marca': 'Marca',
        'producto': 'Producto',
        'Pacas': 'Bultos',
        'codigoZona': 'Cod.',
        'Origen': 'Origen'
    })

    # 2️⃣ Reordenar
    column_order = ['Marca', 'Producto', 'Bultos', 'Cod.','Origen']
    df_reporte = df_reporte[column_order]

    # 3️⃣ Alinear columnas centradas
    center_cols = ['Cod.','Bultos']

    # 4️⃣ Asignar clases personalizadas por columna
    col_classes = {   
        'Marca': 'col-marca',
        'Producto': 'col-producto',
        'Bultos': 'col-bultos align-center',
        'codigoZona' : 'col-cod',
        'Origen': 'col-origen'
    }

    # 5️⃣ Convertir manualmente las filas a HTML
    filas_html = ""
    for _, row in df_reporte.iterrows():
        filas_html += "<tr>"
        for col in df_reporte.columns:
            valor = row[col]
            clase = col_classes.get(col, "")
            filas_html += f'<td class="{clase}">{valor}</td>'
        filas_html += "</tr>"

    # 6️⃣ Renderizar el HTML final con Jinja
    template = JINJA_ENV.get_template(LISTADO_TEMPLATE_FILE)
    final_html = template.render(
        report_table_html=filas_html,
        datos_clave=datos_clave,
        fecha_actual=pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
    )

    return render_to_pdf(final_html)


def generate_bultos_masivo2(df_listado: pd.DataFrame, datos_clave: dict = None) -> bytes:
    """
    Convierte el DataFrame de Listado Total en un PDF binario con columnas ajustadas visualmente.
    """

    # 1️⃣ Renombrar columnas
    df_reporte = df_listado.rename(columns={
        'codigoZona': 'Cod.',
        'Pacas': 'Bultos',
        'Origen': 'Origen',
        'producto': 'Producto',
        'marca': 'Marca'
    })

    # 2️⃣ Reordenar
    column_order = ['Cod.','Marca', 'Producto', 'Bultos', 'Origen']
    df_reporte = df_reporte[column_order ]


    # 4️⃣ Asignar clases personalizadas por columna
    col_classes = {
        'Cod.': 'col-cod',
        'Marca': 'col-marca',
        'Producto': 'col-producto',
        'Bultos': 'col-bultos align-center',
        'Origen': 'col-origen'
    }

# Generar las tablas agrupadas
    tablas_html = ""
    for cod, grupo in df_reporte.groupby('Cod.', sort=True):
        tablas_html += f'<h3>Código de Zona: {cod}</h3>'
        tablas_html += """
        <table class="data-table">
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Marca</th>
                    <th>Producto</th>
                    <th>Bultos</th>
                    <th>Origen</th>
                </tr>
            </thead>
            <tbody>
        """

        for _, row in grupo.iterrows():
            tablas_html += "<tr>"
            for col in column_order:
                valor = row[col]
                clase = col_classes.get(col, "")
                tablas_html += f'<td class="{clase}">{valor}</td>'
            tablas_html += "</tr>"

        tablas_html += "</tbody></table><br/>" 

    # 6️⃣ Renderizar el HTML final con Jinja
    template = JINJA_ENV.get_template(BULTOS_MASIVO_FILE)
    final_html = template.render(
        report_table_html=tablas_html,
        datos_clave=datos_clave,
        fecha_actual=pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
    )

    return render_to_pdf(final_html)


def generate_regueros_zona(df_listado: pd.DataFrame, datos_clave: dict = None) -> bytes:
    """
    Genera un PDF agrupado por Zona y dentro de cada Zona por Origen.
    Cada subgrupo muestra su propia tabla.
    """

    # 1️⃣ Renombrar y asegurar columnas
    df_reporte = df_listado.rename(columns={
        'codigoZona': 'Cod.',
        'marca': 'Marca',
        'producto': 'Producto',
        'Unidades_faltantes': 'Und',
        'origen': 'Origen',
        'zona': 'Zona'
    })

    column_order = ['Cod.','Origen','Marca', 'Producto', 'Und']
    df_reporte = df_reporte[column_order + ['Zona'] ]

    # 2️⃣ Clases por columna
    col_classes = {
        'Cod.': 'col-cod align-center',
        'Origen': 'col-origen',
        'Marca': 'col-marca',
        'Producto': 'col-producto',
        'Und': 'col-und align-center'
    }

    # 3️⃣ Construir el HTML agrupado
    tablas_html = ""
    for zona, grupo_zona in df_reporte.groupby('Zona', sort=True):
        tablas_html += f'<h2>ZONA: {zona}</h2>'

        # Dentro de cada zona, agrupamos por origen
        for origen, grupo_origen in grupo_zona.groupby('Origen', sort=True):
            tablas_html += f'<h3>Origen: {origen}</h3>'
            tablas_html += """
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Origen</th>
                        <th>Marca</th>
                        <th>Producto</th>
                        <th>Bultos</th>
                        
                    </tr>
                </thead>
                <tbody>
            """

            for _, row in grupo_origen.iterrows():
                tablas_html += "<tr>"
                for col in column_order:
                    valor = row[col]
                    clase = col_classes.get(col, "")
                    tablas_html += f'<td class="{clase}">{valor}</td>'
                tablas_html += "</tr>"

            tablas_html += "</tbody></table>"  # Separador entre orígenes

        tablas_html += "<div style='margin-bottom: 1px;'></div>"  # Espacio entre zonas

    # 4️⃣ Renderizar con plantilla Jinja
    template = JINJA_ENV.get_template(REGUEROS_ZONA_FILE)
    final_html = template.render(
        report_table_html=tablas_html,
        datos_clave=datos_clave,
        fecha_actual=pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
    )

    return render_to_pdf(final_html)


def productonegado_pdf(df_listado: pd.DataFrame, datos_clave: dict = None) -> bytes:
    """
    Convierte el DataFrame de Listado Total en un PDF binario con columnas ajustadas visualmente.
    """
    

    # 1️⃣ Renombrar columnas
    df_reporte = df_listado.rename(columns={
        'producto':'Producto',
        'cantidad_negada' : 'Cantidad negada',
        'marca':'Marca',
        'origen': 'Origen',
        'referencia': 'Referencia'
    })


    # 2️⃣ Reordenar
   
    column_order = ['Producto', 'Cantidad negada', 'Marca', 'Origen', 'Referencia']
    df_reporte = df_reporte[column_order]
    

    # 3️⃣ Alinear columnas centradas
    center_cols = [ 'Producto', 'Cantidad negada', 'Marca','Origen', 'Referencia']

    # 4️⃣ Asignar clases personalizadas por columna
    col_classes = {
        'Producto': 'col-producto',
        'Cantidad negada': 'col-negadas align-center',
        'Marca': 'col-marca',
        'Origen': 'col-origen',
        'Referencia': 'col-ref'
    }

    # 5️⃣ Convertir manualmente las filas a HTML
    filas_html = ""
    for _, row in df_reporte.iterrows():
        filas_html += "<tr>"
        for col in df_reporte.columns:
            valor = row[col]
            clase = col_classes.get(col, "")
            filas_html += f'<td class="{clase}">{valor}</td>'
        filas_html += "</tr>"

    # 6️⃣ Renderizar el HTML final con Jinja
    template = JINJA_ENV.get_template(PRODUCTONEGADO_FILE)
    final_html = template.render(
        report_table_html=filas_html,
        datos_clave=datos_clave,
        fecha_actual=pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
    )

    return render_to_pdf(final_html)



def pickingmasivo_pdf_listado(df_listado: pd.DataFrame, datos_clave: dict = None) -> bytes:
    """
    Convierte el DataFrame de Listado Total en un PDF binario con columnas ajustadas visualmente.
    """

    # 1️⃣ Renombrar columnas
    df_reporte = df_listado.rename(columns={
        'marca': 'Marca',
        'producto': 'Producto',
        'unidades': 'Unidades',
        'codigoZona': 'Cod.',
        'Origen': 'Origen'
    })

    # 2️⃣ Reordenar
    column_order = ['Marca', 'Producto', 'Unidades', 'Cod.','Origen']
    df_reporte = df_reporte[column_order]

    # 3️⃣ Alinear columnas centradas
    center_cols = ['Cod.','Unidades']

    # 4️⃣ Asignar clases personalizadas por columna
    col_classes = {   
        'Marca': 'col-marca',
        'Producto': 'col-producto',
        'Unidades': 'col-und align-center',
        'codigoZona' : 'col-cod',
        'Origen': 'col-origen'
    }

    # 5️⃣ Convertir manualmente las filas a HTML
    filas_html = ""
    for _, row in df_reporte.iterrows():
        filas_html += "<tr>"
        for col in df_reporte.columns:
            valor = row[col]
            clase = col_classes.get(col, "")
            filas_html += f'<td class="{clase}">{valor}</td>'
        filas_html += "</tr>"

    # 6️⃣ Renderizar el HTML final con Jinja
    template = JINJA_ENV.get_template(LISTADO_TEMPLATE_PICKMASIVO)
    final_html = template.render(
        report_table_html=filas_html,
        datos_clave=datos_clave,
        fecha_actual=pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
    )

    return render_to_pdf(final_html)