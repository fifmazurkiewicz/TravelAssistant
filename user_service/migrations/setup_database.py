"""
Kompleksowy skrypt migracji - tworzy bazę danych i wykonuje wszystkie migracje
Uruchom: python migrations/setup_database.py
"""
import sys
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker

# Try to get settings from shared.config, fallback to environment variables or local .env
database_url: str | None = None

try:
    from shared.config import get_settings
    settings = get_settings()
    database_url = settings.database_url
except Exception as e:
    import os
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
        print("   Ustaw DATABASE_URL w pliku .env")
        print("   Przykład: DATABASE_URL=postgresql://user:pass@localhost:5432/dbname")
        sys.exit(1)
    
    print(f"✅ Znaleziono DATABASE_URL")
    
# Ensure database_url is not None (type narrowing)
if database_url is None:
    print("❌ BŁĄD: DATABASE_URL jest None!")
    sys.exit(1)

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


def parse_database_url(url: str):
    """Parse database URL to extract components"""
    # Format: postgresql://user:password@host:port/database
    try:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "")
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "")
        else:
            raise ValueError("Invalid database URL format")
        
        # Split auth and rest
        if "@" in url:
            auth_part, rest = url.split("@", 1)
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
            else:
                user = auth_part
                password = ""
        else:
            user = "postgres"
            password = ""
            rest = url
        
        # Split host:port and database
        if "/" in rest:
            host_port, database = rest.split("/", 1)
        else:
            host_port = rest
            database = "postgres"
        
        # Split host and port
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host = host_port
            port = "5432"
        
        return {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": database
        }
    except Exception as e:
        raise ValueError(f"Nie można sparsować DATABASE_URL: {e}")


def create_database_if_not_exists(db_config: dict):
    """Create database if it doesn't exist"""
    db_name = db_config["database"]
    
    # Connect to default postgres database to create new database
    postgres_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/postgres"
    
    print(f"🔍 Sprawdzanie czy baza danych '{db_name}' istnieje...")
    
    try:
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": db_name}
            ).fetchone()
            
            if result:
                print(f"✅ Baza danych '{db_name}' już istnieje")
                return False
            else:
                print(f"➕ Tworzenie bazy danych '{db_name}'...")
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"✅ Baza danych '{db_name}' utworzona pomyślnie!")
                return True
    except OperationalError as e:
        if "password authentication failed" in str(e).lower():
            print(f"❌ Błąd autentykacji do PostgreSQL!")
            print(f"   Sprawdź użytkownika i hasło w DATABASE_URL")
            sys.exit(1)
        elif "could not connect" in str(e).lower():
            print(f"❌ Nie można połączyć się z PostgreSQL!")
            print(f"   Sprawdź czy PostgreSQL jest uruchomiony")
            print(f"   Host: {db_config['host']}, Port: {db_config['port']}")
            sys.exit(1)
        else:
            raise


def run_alembic_migrations(database_url: str):
    """Run Alembic migrations"""
    print("\n📦 Uruchamianie migracji Alembic...")
    
    # Change to user_service directory for alembic
    original_cwd = os.getcwd()
    user_service_dir = Path(__file__).parent.parent
    
    try:
        os.chdir(user_service_dir)
        
        # Check if alembic.ini exists
        if not (user_service_dir / "infrastructure" / "database" / "alembic.ini").exists():
            print("⚠️  Nie znaleziono alembic.ini - pomijam migracje Alembic")
            print("   Utworzę tabele bezpośrednio przez SQLAlchemy")
            return False
        
        # Try to import and run alembic
        try:
            from alembic import command
            from alembic.config import Config
            
            alembic_cfg = Config(str(user_service_dir / "infrastructure" / "database" / "alembic.ini"))
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)
            
            # Check current revision
            try:
                command.current(alembic_cfg)
                print("✅ Sprawdzanie aktualnej wersji migracji...")
            except:
                print("ℹ️  Brak wcześniejszych migracji")
            
            # Run migrations
            print("🔄 Uruchamianie migracji do najnowszej wersji...")
            command.upgrade(alembic_cfg, "head")
            print("✅ Migracje Alembic zakończone pomyślnie!")
            return True
            
        except ImportError:
            print("⚠️  Alembic nie jest zainstalowany - pomijam migracje Alembic")
            print("   Zainstaluj: pip install alembic")
            return False
        except Exception as e:
            print(f"⚠️  Błąd podczas migracji Alembic: {e}")
            print("   Spróbuję utworzyć tabele bezpośrednio")
            return False
            
    finally:
        os.chdir(original_cwd)


def create_tables_directly(database_url: str):
    """Create tables directly using SQLAlchemy models"""
    print("\n📦 Tworzenie tabel bezpośrednio przez SQLAlchemy...")
    
    try:
        from infrastructure.database.models import Base, UserModel, UserPreferencesModel
        
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Create all tables
        print("🔄 Tworzenie tabel users i user_preferences...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabele utworzone pomyślnie!")
        return True
    except Exception as e:
        print(f"❌ Błąd podczas tworzenia tabel: {e}")
        return False


def create_admin_user(database_url: str):
    """Create admin user"""
    print("\n👤 Tworzenie użytkownika admin...")
    
    engine = create_engine(database_url, pool_pre_ping=True)
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
        
    except Exception as e:
        db.rollback()
        print(f"❌ Błąd podczas tworzenia użytkownika admin: {str(e)}")
        raise
    finally:
        db.close()


def main():
    """Main migration function"""
    print("=" * 70)
    print("🚀 Kompleksowa migracja bazy danych - User Service")
    print("=" * 70)
    print()
    
    # Ensure database_url is set
    if not database_url:
        print("❌ BŁĄD: DATABASE_URL nie jest ustawiony!")
        sys.exit(1)
    
    db_url: str = database_url  # Type assertion
    
    try:
        # Step 1: Parse database URL
        print("📋 Krok 1: Parsowanie DATABASE_URL...")
        db_config = parse_database_url(db_url)
        print(f"✅ Parsowanie zakończone:")
        print(f"   Host: {db_config['host']}")
        print(f"   Port: {db_config['port']}")
        print(f"   User: {db_config['user']}")
        print(f"   Database: {db_config['database']}")
        print()
        
        # Step 2: Create database if not exists
        print("📋 Krok 2: Sprawdzanie/Creatowanie bazy danych...")
        db_created = create_database_if_not_exists(db_config)
        print()
        
        # Step 3: Run Alembic migrations or create tables directly
        print("📋 Krok 3: Tworzenie tabel...")
        alembic_success = run_alembic_migrations(db_url)
        
        if not alembic_success:
            # Fallback: create tables directly
            create_tables_directly(db_url)
        print()
        
        # Step 4: Create admin user
        print("📋 Krok 4: Tworzenie użytkownika admin...")
        create_admin_user(db_url)
        print()
        
        print("=" * 70)
        print("🎉 Wszystkie migracje zakończone pomyślnie!")
        print("=" * 70)
        print()
        print("💡 Możesz teraz uruchomić serwis:")
        print("   cd user_service")
        print("   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload")
        print()
        print("📝 Dane logowania admin:")
        print("   Username: admin")
        print("   Password: admin")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ BŁĄD podczas migracji!")
        print("=" * 70)
        print(f"Szczegóły: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

