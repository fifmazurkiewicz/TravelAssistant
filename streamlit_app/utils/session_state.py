"""
Zarządzanie stanem sesji Streamlit
"""
import streamlit as st


def init_session_state():
    """Inicjalizacja stanu sesji"""
    defaults = {
        "access_token": None,
        "user_id": None,
        "username": None,
        "is_admin": False,
        "conversation_history": [],
        "current_conversation": None,
        "current_messages": []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

