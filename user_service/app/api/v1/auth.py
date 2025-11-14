"""
Authentication endpoints
"""
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from shared.config import get_settings

from app.api.v1.schemas import Token, TokenData, UserCreate, UserResponse
from domain.entities.user import User
from domain.ports.authentication_port import IAuthenticationService
from infrastructure.adapters.authentication_adapter import AuthenticationService

router = APIRouter()
settings = get_settings()
# Don't initialize CryptContext here to avoid passlib initialization issues
# We'll use bcrypt directly in authentication_adapter
pwd_context = None  # Kept for compatibility but not used
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def truncate_password_for_bcrypt(password: str) -> str:
    """Truncate password to 72 bytes for bcrypt compatibility"""
    if isinstance(password, bytes):
        password = password.decode('utf-8', errors='ignore')
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return password


def get_authentication_service() -> IAuthenticationService:
    """Dependency injection for authentication service"""
    # TODO: Implement proper DI container
    from infrastructure.adapters.user_repository_adapter import UserRepository
    from infrastructure.database.session import get_db
    db = next(get_db())
    user_repo = UserRepository(db)
    return AuthenticationService(user_repo, pwd_context)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt directly"""
    import bcrypt
    try:
        # Truncate password to 72 bytes for bcrypt compatibility
        truncated_password = truncate_password_for_bcrypt(plain_password)
        return bcrypt.checkpw(truncated_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt directly"""
    import bcrypt
    # Truncate password to 72 bytes for bcrypt compatibility
    truncated_password = truncate_password_for_bcrypt(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(truncated_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: IAuthenticationService = Depends(get_authentication_service)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = await auth_service.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: IAuthenticationService = Depends(get_authentication_service)
):
    """Register new user"""
    # Check if user exists
    existing_user = await auth_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    existing_email = await auth_service.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = await auth_service.create_user(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at
    )


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: IAuthenticationService = Depends(get_authentication_service)
):
    """Login and get access token"""
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

