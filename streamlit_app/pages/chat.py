"""
Strona chat - wyszukiwanie w bazie wiedzy
"""
import streamlit as st

from streamlit_app.utils.api_client import APIClient


def show():
    """Wyświetl stronę chat"""
    st.title("💬 Chat - Wyszukiwanie w bazie wiedzy")
    
    if not st.session_state.access_token:
        st.warning("Zaloguj się, aby korzystać z wyszukiwania")
        return
    
    # Inicjalizacja klienta API
    api_client = APIClient(st.session_state.access_token)
    
    # Inicjalizacja wiadomości
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Wyświetl historię wiadomości
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "results" in message:
                st.json(message["results"])
    
    # Input użytkownika
    if prompt := st.chat_input("Zadaj pytanie..."):
        # Dodaj wiadomość użytkownika
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Wyszukiwanie
        with st.chat_message("assistant"):
            with st.spinner("Szukam odpowiedzi..."):
                try:
                    user_id = st.session_state.user_id if st.session_state.user_id else None
                    results = api_client.search(
                        query=prompt,
                        top_k=5,
                        user_id=user_id
                    )
                    
                    # Wyświetl wyniki
                    if results and "results" in results:
                        st.markdown("**Znalezione wyniki:**")
                        for idx, result in enumerate(results["results"], 1):
                            with st.expander(f"Wynik {idx} (score: {result.get('score', 0):.3f})"):
                                st.markdown(result.get("content", ""))
                                if result.get("metadata"):
                                    st.json(result["metadata"])
                        
                        # Dodaj odpowiedź do historii
                        response_text = f"Znaleziono {results.get('total_results', 0)} wyników dla zapytania: '{prompt}'"
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response_text,
                            "results": results
                        })
                    else:
                        st.info("Nie znaleziono wyników")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "Nie znaleziono wyników dla tego zapytania."
                        })
                except Exception as e:
                    st.error(f"Błąd wyszukiwania: {str(e)}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Wystąpił błąd: {str(e)}"
                    })
    
    # Przycisk do czyszczenia historii
    if st.button("🗑️ Wyczyść historię"):
        st.session_state.messages = []
        st.rerun()

