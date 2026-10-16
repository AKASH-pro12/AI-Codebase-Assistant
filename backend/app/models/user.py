from datetime import datetime, timezone


def create_user_document(name, email, password_hash, role="user"):
    return {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "is_verified": False,
        "is_active": True,
        "role": role,
        "reset_token": None,
        "reset_token_expires": None,
        "verification_otp": None,
        "verification_expires": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }