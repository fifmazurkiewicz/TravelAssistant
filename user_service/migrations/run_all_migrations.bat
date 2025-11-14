@echo off
REM Skrypt do uruchomienia wszystkich migracji (Windows)
REM Użycie: migrations\run_all_migrations.bat

echo 🚀 Uruchamianie migracji User Service...
echo.

REM Sprawdź czy jesteśmy w katalogu user_service
if not exist "infrastructure\database\alembic" (
    echo ❌ Błąd: Uruchom skrypt z katalogu user_service!
    pause
    exit /b 1
)

REM Krok 1: Migracje Alembic (schemat)
echo 📦 Krok 1: Uruchamianie migracji Alembic (schemat bazy danych)...
alembic upgrade head

if %errorlevel% neq 0 (
    echo ❌ Błąd podczas migracji Alembic!
    pause
    exit /b 1
)

echo ✅ Migracje Alembic zakończone
echo.

REM Krok 2: Utworzenie użytkownika admin
echo 👤 Krok 2: Tworzenie użytkownika admin...
python migrations\create_admin_user.py

if %errorlevel% neq 0 (
    echo ⚠️  Ostrzeżenie: Nie udało się utworzyć użytkownika admin (może już istnieć)
)

echo.
echo 🎉 Wszystkie migracje zakończone!
echo.
echo 💡 Możesz teraz uruchomić serwis:
echo    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
echo.
pause

