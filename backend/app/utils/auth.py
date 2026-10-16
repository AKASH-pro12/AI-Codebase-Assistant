
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from bson import ObjectId

from app.database import db
from app.utils.security import decode_access_token

http_bearer = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    token: Optional[str] = Depends(oauth2_scheme),
):
    jwt_token = (bearer.credentials if bearer else None) or token

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(jwt_token)
        user_id = payload.get("sub")

        if not ObjectId.is_valid(user_id):
            raise ValueError("Invalid user ID")

        user = db.users.find_one({
            "_id": ObjectId(user_id)
        })

        if not user:
            raise ValueError("User not found")

        if user.get("is_active", True) is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact an administrator.",
            )

        return user

    except HTTPException:
        raise
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Dependency that ensures the authenticated user has administrative privileges."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


def get_current_active_user(
    current_user: dict = Depends(get_current_user)
):
    return current_user

