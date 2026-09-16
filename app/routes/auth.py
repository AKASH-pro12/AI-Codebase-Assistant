from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.user import create_user_document
from app.schemas.user import UserCreate, UserResponse
from app.utils.security import hash_password


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.get("/")
def auth_status():
    return {
        "message": "Authentication module is ready"
    }


@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate):

    existing_user = db.users.find_one({
        "email": user.email
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    password_hash = hash_password(user.password)

    user_document = create_user_document(
        name=user.name,
        email=user.email,
        password_hash=password_hash
    )

    db.users.insert_one(user_document)

    return {
        "name": user.name,
        "email": user.email,
        "is_verified": False,
        "role": "user"
    }