import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)
JWT_ALGORITHM = "HS256"

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing from environment variables"
    )

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(
    user_id: str,
    email: str,
    role: str = "user"
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expires_at
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise ValueError("Token subject is missing")

        return payload

    except (JWTError, ValueError) as exc:
        raise ValueError("Invalid or expired access token") from exc


COMMON_WEAK_PASSWORDS = {
    "password", "password123", "12345678", "123456789", "qwerty123",
    "admin123", "letmein123", "welcome123", "test1234", "11111111",
    "changeme", "iloveyou123", "abcdefgh"
}


def validate_password_strength(password: str):
    """Authoritative password policy validation.

    Rules:
    - Minimum 8 characters, maximum 72 characters (bcrypt limit).
    - Cannot be a commonly known weak password or repetitive characters.
    - If under 12 characters, must contain at least a mixture of letters and digits or symbols.
    - Long passphrases (>= 12 characters) are welcomed and supported for password managers.
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 72:
        return False, "Password cannot exceed 72 characters."

    clean = password.strip().lower()
    if clean in COMMON_WEAK_PASSWORDS:
        return False, "Password is too common or easily guessed. Please use a stronger password."

    if len(set(clean)) <= 2:
        return False, "Password contains too many repetitive characters."

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)

    # Passphrase friendly: 12+ characters
    if len(password) >= 12:
        return True, None

    # For 8-11 characters, require mix of letters and (numbers or symbols)
    if not has_letter:
        return False, "Password must contain letters."
    if not (has_digit or has_symbol):
        return False, "Passwords under 12 characters must contain numbers or special characters."

    return True, None

