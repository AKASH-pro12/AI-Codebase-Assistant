"""Bootstrap or promote an administrative user.

Usage:
  python -m app.scripts.create_admin yourname@gmail.com
  python -m app.scripts.create_admin --email admin@gmail.com --password SecretPassword123 --name "Admin User"
"""
import sys
import argparse
from datetime import datetime, timezone
from app.database import db
from app.models.user import create_user_document
from app.utils.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create or promote an administrative user")
    parser.add_argument("email_pos", nargs="?", help="Email of the user to promote to admin")
    parser.add_argument("--email", "-e", help="Email of the user")
    parser.add_argument("--password", "-p", help="Password for a new admin user (if creating)")
    parser.add_argument("--name", "-n", default="System Admin", help="Name for a new admin user")

    args = parser.parse_args()
    target_email = (args.email or args.email_pos or "").strip().lower()

    if not target_email:
        print("Error: Email is required. Provide as positional argument or via --email.")
        sys.exit(1)

    existing = db.users.find_one({"email": target_email})

    if existing:
        db.users.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "role": "admin",
                    "is_active": True,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )
        print(f"Success: User '{target_email}' has been promoted to administrator.")
    else:
        if not args.password:
            print(f"User '{target_email}' does not exist. To create a new admin user, provide --password.")
            sys.exit(1)

        password_hash = hash_password(args.password)
        doc = create_user_document(
            name=args.name,
            email=target_email,
            password_hash=password_hash,
            role="admin",
        )
        doc["is_verified"] = True
        doc["is_active"] = True

        db.users.insert_one(doc)
        print(f"Success: New administrator user '{target_email}' created.")


if __name__ == "__main__":
    main()
