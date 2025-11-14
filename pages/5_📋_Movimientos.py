import streamlit as st
import pandas as pd
import requests
from auth_logic import protected_get, logout_user, DJANGO_API_BASE

API_URL = DJANGO_API_BASE + "users/usuarios_movimientos/"

st.set_page_config(page_title="Movimientos", layout="wide") 
st.title("📋 Movimientos del software")

# --- CONTROL DE SESIÓN ---
if not st.session_state.get('logged_in'):
    st.error("🔒 Debe iniciar sesión para acceder a esta página.")
    st.stop()

# --- ESTADO DE DATOS ---
if 'movimientos_data' not in st.session_state:
    st.session_state['movimientos_data'] = pd.DataFrame()


def main():
    
    # 1. BOTÓN DE CONSULTA
    if st.button("Consultar movimientos", type="primary"):
        with st.spinner("Generando reportes ...."):
            try:
                # La petición GET no requiere parámetros en la URL
                response = protected_get(API_URL)
                
                if response is None:
                    st.error("❌ No se obtuvo respuesta del servidor. Verifica la conexión o el endpoint.")
                    return
                
                if response.status_code == 401:
                    st.error("❌ Sesión expirada o no autorizada. Por favor, inicie sesión de nuevo.")
                    logout_user() 
                    return
                
                # 2. ✅ MANEJO DE RESPUESTA Y CÓDIGO DE ESTADO
                if response.status_code == 200: # <-- SE ESPERA 200 OK
                    
                    data_json = response.json()
                    
                    if data_json:
                        df_summary_result = pd.DataFrame(data_json)
                        # ✅ GUARDAR EN ESTADO DE SESIÓN
                        st.session_state['movimientos_data'] = df_summary_result
                        st.success(f"Consulta exitosa. {len(df_summary_result)} movimientos encontrados.")
                    else:
                        st.warning("No se encontraron movimientos registrados.")
                        st.session_state['movimientos_data'] = pd.DataFrame()
                
                elif response.status_code == 404:
                    st.error("❌ Endpoint no encontrado. Revisa la URL del backend.")
                else:
                    st.error(f"❌ Error API: Código {response.status_code}.")
                    st.code(response.json())
                    
                # Forzar el redibujado para que el DataFrame aparezca fuera del botón
                st.rerun() 
                    
            except requests.exceptions.ConnectionError:
                st.error("❌ Error de conexión. Revisa el servidor.")
            except requests.exceptions.JSONDecodeError:
                st.error(f"❌ Error API: El servidor devolvió una respuesta no válida.")
                st.code(response.text)

    # 3. VISUALIZACIÓN DEL DATAFRAME (Se ejecuta en cada rerun)
    if not st.session_state['movimientos_data'].empty:
        st.subheader("Historial de Actividad")
        st.dataframe(
            st.session_state['movimientos_data'], 
            use_container_width=True, 
            hide_index=True
        )


if __name__ == '__main__':
    main()