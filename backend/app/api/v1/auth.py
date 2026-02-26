from fastapi import APIRouter, Depends, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional
from app.core.database import get_async_db
from app.core.security import verify_password, create_access_token, decode_access_token, get_password_hash, validate_password_length
from app.core.rate_limit import limiter
from app.core.token_blacklist import blacklist_token, is_token_blacklisted
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserInDB
from app.core.exceptions import UnauthorizedException, BadRequestException

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _extract_token(request: Request, header_token: Optional[str] = None) -> str:
    """Extract JWT from httpOnly cookie (preferred) or Authorization header (fallback for Swagger)."""
    # 1. Try httpOnly cookie
    token = request.cookies.get("access_token")
    if token:
        return token

    # 2. Fallback to Authorization header (Swagger UI / API clients)
    if header_token:
        return header_token

    raise UnauthorizedException(message="Not authenticated")


async def get_current_user(
    request: Request,
    header_token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Get current authenticated user from cookie or header token"""
    token = _extract_token(request, header_token)

    # Check if token has been revoked (logout blacklist)
    if is_token_blacklisted(token):
        raise UnauthorizedException(message="Token has been revoked")

    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException(message="Could not validate credentials")

    username: str = payload.get("sub")
    if username is None:
        raise UnauthorizedException(message="Could not validate credentials")

    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise UnauthorizedException(message="Could not validate credentials")

    # Store token in request state for downstream use (e.g., logout)
    request.state.token = token

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise BadRequestException(message="Inactive user")
    return current_user


@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
@limiter.limit("5 per minute")
async def register(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Register a new user - 速率限制：每分钟最多5次"""
    # Check if username exists
    existing_user = await db.execute(select(User).filter(User.username == user_data.username))
    if existing_user.scalars().first():
        raise BadRequestException(message="Username already registered")

    # Check if email exists
    existing_email = await db.execute(select(User).filter(User.email == user_data.email))
    if existing_email.scalars().first():
        raise BadRequestException(message="Email already registered")

    # Validate and hash password
    try:
        validate_password_length(user_data.password)
        hashed_password = get_password_hash(user_data.password)
    except ValueError as e:
        raise BadRequestException(message=str(e))

    # Create new user
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.post("/login", response_model=Token)
@limiter.limit("10 per minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    """Login and get access token - 速率限制：每分钟最多10次"""
    # Find user
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedException(message="用户名或密码错误")

    if not user.is_active:
        raise BadRequestException(message="Inactive user")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    # Set httpOnly cookie (immune to XSS)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/api",
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInDB)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
):
    """Logout: blacklist current token and clear httpOnly cookie"""
    # Blacklist the token so it can't be reused
    token = getattr(request.state, "token", None)
    if token:
        blacklist_token(token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    # Clear the httpOnly cookie
    response.delete_cookie(key="access_token", path="/api")

    return {"message": "Successfully logged out"}
