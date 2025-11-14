"""
Strona admin - zarządzanie użytkownikami
"""
import streamlit as st

from streamlit_app.utils.api_client import APIClient


def show():
    """Wyświetl stronę admin"""
    st.title("👤 Panel administracyjny")
    
    if not st.session_state.access_token:
        st.warning("Zaloguj się, aby uzyskać dostęp do panelu administracyjnego")
        return
    
    # Sprawdź czy użytkownik jest administratorem
    if not st.session_state.is_admin:
        st.error("❌ Brak uprawnień! Tylko administratorzy mają dostęp do tego panelu.")
        return
    
    # Inicjalizacja klienta API
    api_client = APIClient(st.session_state.access_token)
    
    st.info("💡 Panel administracyjny - zarządzaj użytkownikami i ich hasłami")
    
    st.subheader("Zarządzanie użytkownikami")
    
    # Lista użytkowników
    if st.button("🔄 Odśwież listę użytkowników"):
        st.rerun()
    
    try:
        users = api_client.list_users()
        
        if users:
            st.write(f"**Znaleziono {len(users)} użytkowników:**")
            
            for user in users:
                with st.expander(f"👤 {user.get('username', 'Bez nazwy')} (ID: {user.get('id')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Email:** {user.get('email', 'N/A')}")
                        st.write(f"**Pełna nazwa:** {user.get('full_name', 'N/A')}")
                    with col2:
                        st.write(f"**Status:** {'✅ Aktywny' if user.get('is_active') else '❌ Nieaktywny'}")
                        st.write(f"**Data utworzenia:** {user.get('created_at', 'N/A')}")
                    
                    st.divider()
                    
                    # Zmiana hasła
                    st.subheader("Zmiana hasła")
                    new_password = st.text_input(
                        "Nowe hasło:",
                        type="password",
                        key=f"password_{user.get('id')}",
                        help="Wpisz nowe hasło dla użytkownika"
                    )
                    confirm_password = st.text_input(
                        "Potwierdź hasło:",
                        type="password",
                        key=f"confirm_{user.get('id')}",
                        help="Potwierdź nowe hasło"
                    )
                    
                    if st.button("Zmień hasło", key=f"btn_change_{user.get('id')}"):
                        if not new_password:
                            st.error("Hasło nie może być puste")
                        elif new_password != confirm_password:
                            st.error("Hasła nie są identyczne")
                        else:
                            with st.spinner("Zmienianie hasła..."):
                                try:
                                    result = api_client.update_user_password(
                                        user_id=user.get('id'),
                                        new_password=new_password
                                    )
                                    st.success(f"✅ Hasło zmienione pomyślnie dla użytkownika {user.get('username')}")
                                    st.json(result)
                                except Exception as e:
                                    st.error(f"❌ Błąd zmiany hasła: {str(e)}")
        else:
            st.info("Brak użytkowników")
    except Exception as e:
        st.error(f"Błąd pobierania użytkowników: {str(e)}")
        st.info("Upewnij się, że masz uprawnienia administratora")

