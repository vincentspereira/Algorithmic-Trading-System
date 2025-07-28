from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from nautilus_trader_engine.database.database import get_db
from nautilus_trader_engine.database.models import User as DBUser
from nautilus_trader_engine.api.models.user import UserInDB
from nautilus_trader_engine.api.utils.auth import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = verify_token(token)
    except Exception:
        raise credentials_exception

    if username is None:
        raise credentials_exception

    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    return UserInDB(**user.__dict__)
