# Streamlit Application - Travel Assistant

Aplikacja Streamlit do interakcji z systemem Travel Assistant.

## Funkcjonalności

1. **Chat-like Search Interface**
   - Wyszukiwanie w bazie wiedzy
   - Historia konwersacji w sidebarze
   - Interaktywny chat

2. **Upload Dokumentów**
   - Przesyłanie plików PDF i DOCX
   - Przeglądanie przesłanych dokumentów
   - Wyszukiwanie w konkretnych dokumentach

3. **Panel Administracyjny**
   - Lista użytkowników
   - Zmiana haseł użytkowników

## Instalacja

```bash
pip install -r streamlit_app/requirements.txt
```

## Uruchomienie

```bash
streamlit run streamlit_app/main.py
```

Aplikacja będzie dostępna pod adresem: http://localhost:8501

## Wymagania

- Wszystkie serwisy backend muszą być uruchomione:
  - User Service (port 8001)
  - Knowledge Base Service (port 8002)
  - Knowledge Management Service (port 8007)
  - Admin Panel Service (port 8006)

## Konfiguracja

URL-e serwisów są konfigurowane w `shared/config.py`. Można je nadpisać przez zmienne środowiskowe w pliku `.env`.

