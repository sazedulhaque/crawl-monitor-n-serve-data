from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, status
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer,
                              OAuth2PasswordBearer)
from jose import JWTError, jwt

from apps.api.models import User
from core.config import settings

# Two authentication schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
bearer_scheme = HTTPBearer(auto_error=False)

# Password hashing
password_hasher = PasswordHasher()


async def get_token(
    oauth2_token: str | None = Depends(oauth2_scheme),
    bearer_token: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """
    Get token from either OAuth2 or Bearer authentication.
    Supports both methods in Swagger UI.
    """
    # Try Bearer token first (direct token input)
    if bearer_token:
        return bearer_token.credentials

    # Fall back to OAuth2 token (username/password flow)
    if oauth2_token:
        return oauth2_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token: str = Depends(get_token)) -> User:
    """Decode JWT token and get current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await User.find_one(User.username == username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return password_hasher.hash(password)


async def authenticate_user(username: str, password: str) -> User | None:
    """Authenticate a user by username and password"""
    user = await User.find_one(User.username == username)
    if not user:
        return None
    return user if user.verify_password(password) else None


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
