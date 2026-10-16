from datetime import datetime, timezone
from typing import Optional, Any
from app.database import db


def log_audit_event(
    user_id: str,
    email: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Record an administrative or security audit event in the database."""
    try:
        audit_record = {
            "user_id": str(user_id),
            "email": str(email),
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "details": details or {},
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc),
        }
        db.audit_logs.insert_one(audit_record)
    except Exception as exc:
        # Audit logging failure should not crash core requests
        print(f"[AuditLogger] Failed to write audit log: {type(exc).__name__}")
