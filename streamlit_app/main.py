"""
Główna aplikacja Streamlit dla Travel Assistant
"""
import sys
from pathlib import Path

import streamlit as st

# Dodaj katalog główny projektu do ścieżki
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from streamlit_app.pages import admin, chat, upload
from streamlit_app.utils.api_client import APIClient
from streamlit_app.utils.session_state import init_session_state

# Konfiguracja strony
st.set_page_config(
    page_title="Travel Assistant",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicjalizacja stanu sesji
init_session_state()

# Sprawdź czy użytkownik jest zalogowany
if "access_token" not in st.session_state:
    st.session_state.access_token = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False

# Sidebar z historią konwersacji i nawigacją
with st.sidebar:
    st.title("✈️ Travel Assistant")
    
    # Logowanie/Wylogowanie
    if st.session_state.access_token:
        st.success(f"Zalogowano jako: {st.session_state.username}")
        if st.button("Wyloguj"):
            st.session_state.access_token = None
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.is_admin = False
            st.session_state.conversation_history = []
            st.rerun()
    else:
        st.info("Zaloguj się, aby korzystać z aplikacji")
        with st.expander("Logowanie", expanded=True):
            username = st.text_input("Nazwa użytkownika")
            password = st.text_input("Hasło", type="password")
            if st.button("Zaloguj"):
                api_client = APIClient()
                try:
                    token_data = api_client.login(username, password)
                    if token_data:
                        st.session_state.access_token = token_data["access_token"]
                        # Pobierz informacje o użytkowniku
                        api_client_with_token = APIClient(st.session_state.access_token)
                        user_info = api_client_with_token.get_current_user()
                        if user_info:
                            st.session_state.user_id = user_info.get("id")
                            st.session_state.username = user_info.get("username")
                            st.session_state.is_admin = user_info.get("is_admin", False)
                        st.success("Zalogowano pomyślnie!")
                        st.rerun()
                    else:
                        st.error("Błędna nazwa użytkownika lub hasło")
                except Exception as e:
                    st.error(f"Błąd logowania: {str(e)}")
    
    st.divider()
    
    # Historia konwersacji
    if st.session_state.access_token:
        st.subheader("Historia konwersacji")
        if "conversation_history" not in st.session_state:
            st.session_state.conversation_history = []
        
        if st.session_state.conversation_history:
            for idx, conv in enumerate(st.session_state.conversation_history):
                if st.button(f"📝 {conv.get('title', f'Konwersacja {idx+1}')[:30]}", key=f"conv_{idx}"):
                    st.session_state.current_conversation = idx
                    st.rerun()
        else:
            st.info("Brak historii konwersacji")
        
        if st.button("➕ Nowa konwersacja"):
            st.session_state.current_conversation = None
            st.session_state.current_messages = []
            st.rerun()
    
    st.divider()
    
    # Nawigacja
    st.subheader("Nawigacja")
    pages = ["Chat", "Upload"]
    # Panel admin dostępny tylko dla administratorów
    if st.session_state.access_token and st.session_state.is_admin:
        pages.append("Admin")
    
    page = st.radio(
        "Wybierz stronę:",
        pages,
        key="page_selector"
    )

# Główna zawartość
if page == "Chat":
    chat.show()
elif page == "Upload":
    upload.show()
elif page == "Admin":
    admin.show()

