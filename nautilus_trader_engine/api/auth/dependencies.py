from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from sqlalchemy.orm import Session

from nautilus_trader_engine.database.database import get_db
from nautilus_trader_engine.database.models import User as DBUser
from nautilus_trader_engine.api.models.user import UserInDB
from ..core.security import verify_token as verify_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
security = HTTPBearer()

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = verify_jwt(token, token_type="access")
    except Exception:
        raise credentials_exception

    if not user_id:
        raise credentials_exception

    return user_id


def verify_refresh_token(token: str) -> str:
    """
    Verify a refresh token and return the associated user ID.
    Raises HTTPException 401 if invalid/expired.
    """
    try:
        user_id = verify_jwt(token, token_type="refresh")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
