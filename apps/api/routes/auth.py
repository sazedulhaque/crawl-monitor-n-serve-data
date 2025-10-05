from datetime import timedelta
from typing import Annotated

from beanie.operators import Or
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from apps.api.models import User
from apps.api.schemas import Token, UserRegister
from apps.utils.auth import (authenticate_user, create_access_token,
                             get_current_active_user)
from core.config import settings

router = APIRouter()


@router.post(
    "/register",
    response_model=User,
    response_model_exclude={"password", "created_at", "updated_at", "id"},
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserRegister,
):
    """Register a new user"""
    # Check if user already exists
    existing_user = await User.find_one(
        Or(User.username == user_data.username, User.email == user_data.email)
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
    )
    await user.save(hash_password=True)
    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return JWT token"""
    user = await User.find_one(User.username == form_data.username)
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(hours=24)
    )
    return Token(access_token=access_token)


@router.get(
    "/me",
    response_model=User,
    response_model_exclude={"password", "created_at", "updated_at", "id"},
)
async def read_users_me_and_scrape(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Get current user information"""
    # User information
    return await User.get(current_user.id)


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
