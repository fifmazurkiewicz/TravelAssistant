# Travel Assistant AI

Inteligentna aplikacja AI do planowania podróży wykorzystująca zaawansowane techniki AI (Agentic AI, RAG, Model-Controlled Planning).

## Architektura

Projekt wykorzystuje:
- **Domain-Driven Design (DDD)**
- **Hexagonal Architecture (Ports & Adapters)**
- **Clean Architecture**
- **Model-Controlled Planning (MCP)**
- **Microservices** (monorepo structure)

## Struktura Projektu

```
TravelAssistant/
├── user_service/              # Zarządzanie użytkownikami i autentykacją
├── knowledge_base_service/    # Baza wiedzy z RAG
├── flight_search_service/     # Wyszukiwanie lotów
├── hotel_booking_service/     # Rezerwacja hoteli
├── trip_planning_service/     # Główny orchestrator z MCP
├── admin_panel_service/       # Panel administracyjny
├── shared/                    # Współdzielone komponenty
├── research/                  # Narzędzia R&D
│   ├── quality_assessment/
│   ├── benchmarking/
│   └── notebooks/
└── docker-compose.yml
```

## Wymagania

- Python 3.11+
- uv (dependency manager)
- Docker & Docker Compose
- PostgreSQL 15+

## Instalacja

1. **Sklonuj repozytorium:**
```bash
git clone <repository-url>
cd TravelAssistant
```

2. **Skonfiguruj zmienne środowiskowe:**
```bash
cp .env.example .env
# Edytuj .env i uzupełnij wymagane klucze API
```

3. **Uruchom kontenery Docker:**
```bash
docker-compose up -d
```

4. **Zainstaluj zależności:**

**Opcja A: Wspólne venv (zalecane dla developmentu)**
```bash
# Z katalogu głównego
uv sync
```

**Opcja B: Osobne venv dla każdego serwisu**
```bash
cd user_service && uv sync
cd ../knowledge_base_service && uv sync
# ... itd.
```

Zobacz [VENV_OPTIONS.md](VENV_OPTIONS.md) dla szczegółów.

5. **Uruchom migracje bazy danych:**
```bash
# Dla każdego serwisu z bazą danych
cd user_service
alembic upgrade head
```

## Uruchomienie Lokalne

Każdy serwis można uruchomić niezależnie:

```bash
# User Service
cd user_service
uvicorn app.main:app --reload --port 8001

# Knowledge Base Service
cd knowledge_base_service
uvicorn app.main:app --reload --port 8002

# Flight Search Service
cd flight_search_service
uvicorn app.main:app --reload --port 8003

# Hotel Booking Service
cd hotel_booking_service
uvicorn app.main:app --reload --port 8004

# Trip Planning Service
cd trip_planning_service
uvicorn app.main:app --reload --port 8005

# Admin Panel Service
cd admin_panel_service
uvicorn app.main:app --reload --port 8006
```

## Konfiguracja

Wszystkie ustawienia znajdują się w pliku `.env`. Kluczowe konfiguracje:

- **DATABASE_URL**: Połączenie z PostgreSQL
- **VECTOR_DB_TYPE**: Typ bazy wektorowej (qdrant/weaviate/chroma)
- **OPENROUTER_API_KEY**: Klucz API do OpenRouter
- **EMBEDDING_MODEL**: Model do embeddings

## Dokumentacja API

Po uruchomieniu serwisów, dokumentacja Swagger/OpenAPI dostępna jest pod:
- User Service: http://localhost:8001/docs
- Knowledge Base Service: http://localhost:8002/docs
- Trip Planning Service: http://localhost:8005/docs
- itd.

## R&D i Benchmarking

Moduły badawcze znajdują się w katalogu `research/`:
- `quality_assessment/`: Ocena jakości retrieval i generation
- `benchmarking/`: Benchmarking modeli LLM, embeddingów, vector DB
- `notebooks/`: Jupyter notebooks do eksperymentów

## Licencja

MIT
