"""
Strona upload - przesyłanie i przeglądanie dokumentów
"""
import streamlit as st

from streamlit_app.utils.api_client import APIClient


def show():
    """Wyświetl stronę upload"""
    st.title("📤 Upload dokumentów")
    
    if not st.session_state.access_token:
        st.warning("Zaloguj się, aby przesyłać dokumenty")
        return
    
    # Inicjalizacja klienta API
    api_client = APIClient(st.session_state.access_token)
    
    # Tabs
    tab1, tab2 = st.tabs(["📤 Upload", "📋 Moje dokumenty"])
    
    with tab1:
        st.subheader("Prześlij dokument")
        st.info("Obsługiwane formaty: PDF, DOCX")
        
        uploaded_file = st.file_uploader(
            "Wybierz plik",
            type=["pdf", "docx"],
            help="Maksymalny rozmiar pliku: 50MB"
        )
        
        if uploaded_file is not None:
            # Wyświetl informacje o pliku
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Nazwa pliku:** {uploaded_file.name}")
            with col2:
                st.write(f"**Rozmiar:** {uploaded_file.size / 1024:.2f} KB")
            
            if st.button("Prześlij dokument"):
                with st.spinner("Przesyłanie i przetwarzanie dokumentu..."):
                    try:
                        file_content = uploaded_file.read()
                        result = api_client.upload_document(
                            file_content=file_content,
                            filename=uploaded_file.name,
                            content_type=uploaded_file.type
                        )
                        st.success(f"✅ Dokument przesłany pomyślnie!")
                        st.json(result)
                    except Exception as e:
                        st.error(f"❌ Błąd przesyłania: {str(e)}")
    
    with tab2:
        st.subheader("Moje dokumenty")
        
        if st.button("🔄 Odśwież listę"):
            st.rerun()
        
        try:
            documents = api_client.list_documents()
            
            if documents:
                st.write(f"**Znaleziono {len(documents)} dokumentów:**")
                
                for doc in documents:
                    with st.expander(f"📄 {doc.get('filename', 'Bez nazwy')} (ID: {doc.get('id')})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Typ:** {doc.get('content_type', 'N/A')}")
                        with col2:
                            st.write(f"**Rozmiar:** {doc.get('file_size', 0) / 1024:.2f} KB")
                        with col3:
                            st.write(f"**Data:** {doc.get('created_at', 'N/A')}")
                        
                        # Wyszukiwanie w dokumencie
                        st.divider()
                        st.subheader("Wyszukaj w tym dokumencie")
                        search_query = st.text_input(
                            "Zapytanie:",
                            key=f"search_{doc.get('id')}",
                            placeholder="Wpisz pytanie..."
                        )
                        if st.button("Szukaj", key=f"btn_search_{doc.get('id')}"):
                            if search_query:
                                with st.spinner("Szukam..."):
                                    try:
                                        results = api_client.search(
                                            query=search_query,
                                            top_k=3
                                        )
                                        if results and "results" in results:
                                            for idx, result in enumerate(results["results"], 1):
                                                with st.expander(f"Wynik {idx}"):
                                                    st.markdown(result.get("content", ""))
                                                    if result.get("metadata"):
                                                        st.json(result["metadata"])
                                        else:
                                            st.info("Nie znaleziono wyników")
                                    except Exception as e:
                                        st.error(f"Błąd wyszukiwania: {str(e)}")
            else:
                st.info("Brak przesłanych dokumentów")
        except Exception as e:
            st.error(f"Błąd pobierania dokumentów: {str(e)}")

