"""
Skrypt migracji: Tworzenie użytkownika admin

Sposoby uruchomienia:
1. Z katalogu głównego projektu:
   python -m user_service.migrations.create_admin_user

2. Z katalogu user_service (zalecane):
   python migrations/create_admin_user.py

3. Bezpośrednio:
   python user_service/migrations/create_admin_user.py
"""
import sys
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Try to get settings from shared.config, fallback to environment variables or local .env
try:
    from shared.config import get_settings
    settings = get_settings()
    database_url = settings.database_url
except Exception as e:
    import os
    from pathlib import Path
    
    print(f"⚠️  Nie można załadować konfiguracji z shared.config: {e}")
    print("💡 Sprawdzam zmienne środowiskowe i lokalne pliki .env...")
    
    # Try environment variable first
    database_url = os.getenv("DATABASE_URL")
    
    # If not found, try to load from local .env file (user_service/.env)
    if not database_url:
        local_env = Path(__file__).parent.parent / ".env"
        if local_env.exists():
            print(f"📁 Znaleziono lokalny plik .env: {local_env}")
            try:
                from dotenv import load_dotenv
                load_dotenv(local_env)
                database_url = os.getenv("DATABASE_URL")
            except ImportError:
                # Try manual parsing
                with open(local_env, 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            database_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
    
    # If still not found, try root .env
    if not database_url:
        root_env = project_root / ".env"
        if root_env.exists():
            print(f"📁 Znaleziono plik .env w katalogu głównym: {root_env}")
            try:
                from dotenv import load_dotenv
                load_dotenv(root_env)
                database_url = os.getenv("DATABASE_URL")
            except ImportError:
                # Try manual parsing
                with open(root_env, 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            database_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
    
    if not database_url:
        print("❌ BŁĄD: Brak DATABASE_URL!")
        print("   Sprawdzane lokalizacje:")
        print(f"   - Zmienne środowiskowe")
        print(f"   - {local_env}")
        print(f"   - {root_env}")
        print("   Ustaw DATABASE_URL w jednym z powyższych miejsc")
        print("   Przykład: DATABASE_URL=postgresql://user:pass@localhost:5432/dbname")
        sys.exit(1)
    
    print(f"✅ Znaleziono DATABASE_URL")


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly with 72-byte limit handling"""
    # Bcrypt has a 72-byte limit, truncate if necessary
    if isinstance(password, bytes):
        password = password.decode('utf-8', errors='ignore')
    # Truncate to 72 bytes (not characters) to avoid bcrypt error
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
        print(f"⚠️  Ostrzeżenie: Hasło zostało obcięte do 72 bajtów")
    # Use bcrypt directly to avoid passlib initialization issues
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Return as string (bcrypt format is compatible with passlib)
    return hashed.decode('utf-8')


def create_admin_user():
    """Create admin user with username 'admin' and password 'admin'"""
    # Ensure database_url is not None
    if database_url is None:
        print("❌ BŁĄD: DATABASE_URL jest None!")
        return
    
    # Create database connection
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Połączenie z bazą danych OK")
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower():
            print("❌ BŁĄD: Baza danych nie istnieje!")
            print("")
            print("💡 Rozwiązanie:")
            print("   1. Utwórz bazę danych:")
            print("      psql -U postgres -c \"CREATE DATABASE TravelAssistant;\"")
            print("")
            print("   2. Lub zmień DATABASE_URL w pliku .env na istniejącą bazę")
            print("")
            print("   3. Następnie uruchom ten skrypt ponownie")
            print("")
            print(f"   Szczegóły błędu: {error_msg}")
            sys.exit(1)
        else:
            raise
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if is_admin column exists, if not add it
        print("🔍 Sprawdzanie kolumny is_admin...")
        try:
            db.execute(text("SELECT is_admin FROM users LIMIT 1"))
            print("✅ Kolumna is_admin już istnieje")
        except Exception:
            print("➕ Dodawanie kolumny is_admin...")
            db.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL"))
            db.commit()
            print("✅ Kolumna is_admin dodana")
        
        # Check if admin user already exists
        result = db.execute(
            text("SELECT id, username, is_admin FROM users WHERE username = :username"),
            {"username": "admin"}
        ).fetchone()
        
        if result:
            user_id, username, is_admin = result
            if is_admin:
                print(f"✅ Użytkownik 'admin' już istnieje i jest administratorem (ID: {user_id})")
                print("💡 Jeśli chcesz zresetować hasło, usuń użytkownika i uruchom skrypt ponownie")
            else:
                # Update existing user to admin
                print(f"🔄 Aktualizowanie użytkownika 'admin' do roli administratora...")
                hashed_password = hash_password("admin")
                db.execute(
                    text("""
                        UPDATE users 
                        SET is_admin = TRUE, 
                            hashed_password = :hashed_password,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE username = :username
                    """),
                    {"username": "admin", "hashed_password": hashed_password}
                )
                db.commit()
                print("✅ Użytkownik 'admin' zaktualizowany do roli administratora")
        else:
            # Create new admin user
            print("➕ Tworzenie nowego użytkownika admin...")
            hashed_password = hash_password("admin")
            
            db.execute(
                text("""
                    INSERT INTO users (username, email, hashed_password, full_name, is_active, is_admin, created_at)
                    VALUES (:username, :email, :hashed_password, :full_name, :is_active, :is_admin, CURRENT_TIMESTAMP)
                """),
                {
                    "username": "admin",
                    "email": "admin@travelassistant.local",
                    "hashed_password": hashed_password,
                    "full_name": "Administrator",
                    "is_active": True,
                    "is_admin": True
                }
            )
            db.commit()
            print("✅ Użytkownik 'admin' utworzony pomyślnie!")
            print("   Username: admin")
            print("   Password: admin")
            print("   Email: admin@travelassistant.local")
            print("   Role: Administrator")
        
        print("\n🎉 Migracja zakończona pomyślnie!")
        print("\n💡 Możesz się teraz zalogować w Streamlit:")
        print("   Username: admin")
        print("   Password: admin")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Błąd podczas migracji: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migracja: Tworzenie użytkownika admin")
    print("=" * 60)
    print()
    create_admin_user()

