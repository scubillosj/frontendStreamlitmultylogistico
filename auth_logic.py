# auth_logic.py
import streamlit as st
import requests
import json
from streamlit_browser_storage import LocalStorage
from requests.exceptions import RequestException
from datetime import date, datetime

# === CONFIGURACIÓN ===
DJANGO_API_BASE = "https://multy-logisticaapp-z5y3m.ondigitalocean.app/api/"
LOGIN_URL = DJANGO_API_BASE + "auth/jwt/create/"
REFRESH_URL = DJANGO_API_BASE + "auth/jwt/refresh/"
REGISTER_URL = DJANGO_API_BASE + "register/users/"

# === ALMACENAMIENTO PERSISTENTE ===
storage = LocalStorage(key="auth_tokens")


# ===============================================================
# 🔹 INICIALIZACIÓN DEL ESTADO DE SESIÓN
# ===============================================================
def init_session_state():
    """Inicializa o recupera sesión del almacenamiento local."""
    if 'initialized' in st.session_state:
        return
    st.session_state['initialized'] = True

    # 🔹 Recuperar tokens del navegador
    stored_access = storage.get("access_token")
    stored_refresh = storage.get("refresh_token")
    stored_username = storage.get("username")
    
    # 💡 AJUSTE: Si hay tokens, ASUME que está logueado temporalmente.
    if stored_access and stored_refresh:
        st.session_state['access_token'] = stored_access
        st.session_state['refresh_token'] = stored_refresh
        st.session_state['username'] = stored_username
        st.session_state['logged_in'] = True
    else:
        # No hay tokens, inicializa vacío
        st.session_state['logged_in'] = False
        st.session_state['access_token'] = None
        st.session_state['refresh_token'] = None
        st.session_state['username'] = None
        
    # Inicialización de banderas auxiliares si no existen
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False

# ===============================================================
# 🔹 LOGIN / LOGOUT
# ===============================================================
def login_user(username, password):
    try:
        response = requests.post(LOGIN_URL, json={"username": username, "password": password})
        
        if response.status_code == 200:
            tokens = response.json()
            
            # Guardar tokens y estado en sesión
            st.session_state['access_token'] = tokens['access']
            st.session_state['refresh_token'] = tokens['refresh']
            st.session_state['username'] = username
            st.session_state['logged_in'] = True

            # 🔹 También guardarlos en LocalStorage (persistente)
            storage.set("access_token", tokens['access'])
            storage.set("refresh_token", tokens['refresh'])
            storage.set("username", username)

            st.success(f"Bienvenido, {username}!")
            st.rerun()
            return True
        else:
            st.error("Credenciales inválidas.")
            return False
    except requests.exceptions.ConnectionError:
        st.error("Error de conexión. Verifica que el backend esté corriendo.")
        return False


def logout_user():
    """Cierra sesión limpiando tanto sesión como almacenamiento local."""
    # Limpia session_state
    st.session_state['logged_in'] = False
    st.session_state['access_token'] = None
    st.session_state['refresh_token'] = None
    st.session_state['username'] = None

    # Limpia localStorage
    storage.delete("access_token")
    storage.delete("refresh_token")
    storage.delete("username")

    st.rerun()

# ===============================================================
# 🔹 REFRESH TOKEN
# ===============================================================
def refresh_access_token(silent=False):
    """Usa el refresh token para renovar el access token."""
    refresh_token = st.session_state.get("refresh_token")
    if not refresh_token:
        return False

    try:
        response = requests.post(
            REFRESH_URL,
            json={"refresh": refresh_token},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            tokens = response.json()
            st.session_state["access_token"] = tokens["access"]

            # Actualizar en navegador
            storage.set("access_token", tokens["access"])

            if "refresh" in tokens:
                st.session_state["refresh_token"] = tokens["refresh"]
                storage.set("refresh_token", tokens["refresh"])

            if not silent:
                st.toast("🔄 Token renovado automáticamente", icon="✅")

            return True
        else:
            if not silent:
                st.warning("⚠️ Sesión expirada. Por favor, vuelve a iniciar sesión.")
            logout_user()
            return False

    except requests.exceptions.RequestException:
        if not silent:
            st.error("Error de red durante el refresco del token.")
        return False


# ===============================================================
# 🔹 UTILIDADES DE AUTENTICACIÓN
# ===============================================================
def get_auth_headers():
    """Encabezados con token Bearer."""
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


# ===============================================================
# 🔹 PETICIONES PROTEGIDAS (con auto-refresh)
# ===============================================================
def protected_request_with_retry(method, url, data=None, json=None):
    """Realiza una petición autenticada y refresca el token si expira."""
    headers = get_auth_headers()
    kwargs = {"headers": headers}
    if data is not None:
        kwargs["data"] = data
    if json is not None:
        kwargs["json"] = json

    response = requests.request(method, url, **kwargs)

    if response.status_code == 401:
        st.warning("⏳ Token expirado. Intentando renovar...")
        if refresh_access_token(silent=True):
            headers = get_auth_headers()
            kwargs["headers"] = headers
            response = requests.request(method, url, **kwargs)
        else:
            logout_user()

    return response


def protected_get(url):
    return protected_request_with_retry("GET", url)

def protected_post(url, data):
    """Envía una solicitud POST autenticada, asegurando que las fechas sean serializables."""
    
    # ✅ Conversor seguro para fechas y valores no serializables
    def default_converter(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if pd.isna(o):
            return None
        return str(o)

    try:
        # Serialización robusta
        json_data = json.dumps(data, default=default_converter)

        # Enviar la solicitud usando tu función con autenticación y reintentos
        response = protected_request_with_retry("POST", url, data=json_data)
        return response

    except TypeError as e:
        st.error(f"⚠️ Error al serializar los datos: {e}")
        return None
    except RequestException as e:
        st.error(f"❌ Error de red al contactar con el servidor: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado en protected_post: {e}")
        return None

def protected_patch(url, data):
    return protected_request_with_retry("PATCH", url, json=data)


# ===============================================================
# 🔹 FORMULARIOS UI (para login / registro)
# ===============================================================
def show_login_form():
    """Renderiza el formulario de inicio de sesión."""
    st.header("🔐 Iniciar Sesión")
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            with st.spinner("Autenticando..."):
                login_user(username, password)


def register_user(username, email, password, re_password):
    """Crea un nuevo usuario en Django."""
    data = {
        "username": username,
        "email": email,
        "password": password,
        "re_password": re_password,
    }
    try:
        response = requests.post(REGISTER_URL, json=data)
        if response.status_code == 201:
            st.success("🎉 Registro exitoso. Ahora puedes iniciar sesión.")
            return True
        else:
            st.error("Error en el registro.")
            st.json(response.json())
            return False
    except requests.exceptions.ConnectionError:
        st.error("Error de conexión con el backend de Django.")
        return False


def show_register_form():
    """Renderiza el formulario de registro."""
    st.header("🧾 Crear nueva cuenta")
    with st.form("register_form"):
        username = st.text_input("Usuario")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        re_password = st.text_input("Repetir contraseña", type="password")
        submitted = st.form_submit_button("Registrarse")

        if submitted:
            with st.spinner("Creando cuenta..."):
                if register_user(username, email, password, re_password):
                    st.session_state["show_register"] = False
                    st.rerun()
