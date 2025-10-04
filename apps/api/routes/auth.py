from datetime import timedelta
from typing import Annotated

from beanie.operators import Or
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from apps.api.models import User
from apps.api.schemas import Token, UserRegister, UserResponse
from apps.utils.auth import (authenticate_user, create_access_token,
                             get_current_active_user)
from core.config import settings

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserRegister):
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

    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        password=User.get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    await user.insert()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
    )


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


@router.get("/me")
async def read_users_me_and_scrape(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Get current user information"""
    # User information
    user_response = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )

    return {"user": user_response.model_dump()}


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
