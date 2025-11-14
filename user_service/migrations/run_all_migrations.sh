#!/bin/bash
# Skrypt do uruchomienia wszystkich migracji
# Użycie: bash migrations/run_all_migrations.sh

echo "🚀 Uruchamianie migracji User Service..."
echo ""

# Sprawdź czy jesteśmy w katalogu user_service
if [ ! -d "infrastructure/database/alembic" ]; then
    echo "❌ Błąd: Uruchom skrypt z katalogu user_service!"
    exit 1
fi

# Krok 1: Migracje Alembic (schemat)
echo "📦 Krok 1: Uruchamianie migracji Alembic (schemat bazy danych)..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Błąd podczas migracji Alembic!"
    exit 1
fi

echo "✅ Migracje Alembic zakończone"
echo ""

# Krok 2: Utworzenie użytkownika admin
echo "👤 Krok 2: Tworzenie użytkownika admin..."
python migrations/create_admin_user.py

if [ $? -ne 0 ]; then
    echo "⚠️  Ostrzeżenie: Nie udało się utworzyć użytkownika admin (może już istnieć)"
fi

echo ""
echo "🎉 Wszystkie migracje zakończone!"
echo ""
echo "💡 Możesz teraz uruchomić serwis:"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"

