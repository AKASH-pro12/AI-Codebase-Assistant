from datetime import datetime, timezone


def create_user_document(name, email, password_hash):
    return {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "is_verified": False,
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }