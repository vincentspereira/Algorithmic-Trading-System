from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from nautilus_trader_engine.database import models
from nautilus_trader_engine.database.database import get_db
from nautilus_trader_engine.api.models.auth import UserInfo as UserResponse
from pydantic import BaseModel, Field
from nautilus_trader_engine.api.auth.dependencies import get_current_user
from nautilus_trader_engine.api.models.user import UserInDB

class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, description="New email address for the user")
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")

    class Config:
        schema_extra = {
            "example": {
                "email": "new.email@example.com",
                "is_active": True,
            }
        }

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve the currently authenticated user's information.
    """
    return UserResponse(user_id=str(current_user.id), username=current_user.username, is_active=current_user.is_active)

@router.get("/{user_id}", response_model=UserResponse)
async def read_user_by_id(user_id: int, db: Session = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve a user by their ID.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(user_id=str(user.id), username=user.username, is_active=user.is_active, created_at=str(user.id))

@router.get("/username/{username}", response_model=UserResponse)
async def read_user_by_username(username: str, db: Session = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve a user by their username.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(user_id=str(user.id), username=user.username, is_active=user.is_active, created_at=str(user.id))

@router.get("/", response_model=List[UserResponse])
async def read_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve a list of all users. (Admin only)
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [UserResponse(user_id=str(user.id), username=user.username, is_active=user.is_active, created_at=str(user.id)) for user in users]

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    """
    Update user information by ID.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_update.email is not None:
        user.email = user_update.email
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(user_id=str(user.id), username=user.username, is_active=user.is_active, created_at=str(user.id))