from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.database import get_async_db
from app.models.user import User
from app.schemas.user import UserInDB, UserUpdate
from app.api.v1.auth import get_current_active_user
from app.core.exceptions import NotFoundException, PermissionDeniedException

router = APIRouter()


@router.get("/", response_model=List[UserInDB])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all users (admin only)"""
    if current_user.role not in ["admin", "superuser"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserInDB)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user by ID"""
    # Users can only view their own profile unless they're admin
    if current_user.id != user_id and current_user.role not in ["admin", "superuser"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise NotFoundException(message="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserInDB)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update user"""
    # Users can only update their own profile unless they're admin
    if current_user.id != user_id and current_user.role not in ["admin", "superuser"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise NotFoundException(message="User not found")
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete user (admin only)"""
    if current_user.role not in ["admin", "superuser"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise NotFoundException(message="User not found")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}
