import os
import shutil
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.database import db
from app.utils.auth import require_admin
from app.schemas.user import UserStatusUpdateRequest, UserRoleUpdateRequest
from app.services.audit import log_audit_event
from app.services.file_processor import UPLOAD_DIR

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(require_admin)]
)


@router.get("/stats")
def get_system_stats():
    """Retrieve high-level system statistics for the admin dashboard."""
    total_users = db.users.count_documents({})
    active_users = db.users.count_documents({"is_active": {"$ne": False}})
    total_codebases = db.codebases.count_documents({})
    total_chunks = db.code_chunks.count_documents({})
    total_audit_logs = db.audit_logs.count_documents({})

    return {
        "total_users": total_users,
        "active_users": active_users,
        "deactivated_users": total_users - active_users,
        "total_codebases": total_codebases,
        "total_chunks": total_chunks,
        "total_audit_logs": total_audit_logs,
    }


@router.get("/users")
def list_users():
    """List all registered users with their roles, statuses, and repository counts."""
    users = list(db.users.find({}, {"password_hash": 0, "reset_token": 0, "verification_otp": 0}).sort("created_at", -1))

    # Pre-count codebases per user
    pipeline = [
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}
    ]
    counts_map = {doc["_id"]: doc["count"] for doc in db.codebases.aggregate(pipeline)}

    user_list = []
    for u in users:
        u_id = str(u["_id"])
        user_list.append({
            "id": u_id,
            "_id": u_id,
            "name": u.get("name", "User"),
            "email": u.get("email"),
            "role": u.get("role", "user"),
            "is_active": u.get("is_active", True),
            "is_verified": u.get("is_verified", False),
            "created_at": u.get("created_at"),
            "codebase_count": counts_map.get(u_id, 0),
        })

    return {
        "total": len(user_list),
        "users": user_list,
    }


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    body: UserStatusUpdateRequest,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Activate or deactivate a user account."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    if str(admin["_id"]) == user_id and body.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account",
        )

    target_user = db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": body.is_active, "updated_at": datetime.now(timezone.utc)}}
    )

    action = "USER_ACTIVATED" if body.is_active else "USER_DEACTIVATED"
    log_audit_event(
        user_id=str(admin["_id"]),
        email=admin["email"],
        action=action,
        resource_type="user",
        resource_id=user_id,
        details={"target_email": target_user.get("email"), "new_status": body.is_active},
        ip_address=request.client.host if request.client else None,
    )

    return {
        "message": f"User account successfully {'activated' if body.is_active else 'deactivated'}",
        "user_id": user_id,
        "is_active": body.is_active,
    }


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    body: UserRoleUpdateRequest,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Promote or demote a user role."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    target_user = db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent demoting the last active administrator
    if str(admin["_id"]) == user_id and body.role != "admin":
        admin_count = db.users.count_documents({"role": "admin", "is_active": {"$ne": False}})
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only remaining administrator",
            )

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": body.role, "updated_at": datetime.now(timezone.utc)}}
    )

    log_audit_event(
        user_id=str(admin["_id"]),
        email=admin["email"],
        action="USER_ROLE_CHANGED",
        resource_type="user",
        resource_id=user_id,
        details={"target_email": target_user.get("email"), "new_role": body.role},
        ip_address=request.client.host if request.client else None,
    )

    return {
        "message": f"User role successfully updated to {body.role}",
        "user_id": user_id,
        "role": body.role,
    }


@router.get("/audit-logs")
def get_audit_logs():
    """Retrieve the recent security and administrative audit logs."""
    raw_logs = list(
        db.audit_logs.find({})
        .sort("timestamp", -1)
        .limit(100)
    )
    logs = []
    for log in raw_logs:
        oid = str(log.get("_id", ""))
        log["id"] = oid
        log["_id"] = oid
        logs.append(log)

    return {
        "total": len(logs),
        "audit_logs": logs,
    }


@router.get("/codebases")
def list_all_codebases():
    """List all codebases across all users."""
    raw_codebases = list(
        db.codebases.find(
            {},
            {"codebase_id": 1, "codebase_name": 1, "user_id": 1, "total_files": 1, "created_at": 1}
        ).sort("created_at", -1)
    )

    codebases = []
    for cb in raw_codebases:
        db_id = str(cb.get("_id", ""))
        cb_id = cb.get("codebase_id") or db_id
        cb["id"] = db_id
        cb["_id"] = db_id
        cb["codebase_id"] = cb_id
        codebases.append(cb)

    # Attach user emails for readability
    user_ids = {cb.get("user_id") for cb in codebases if cb.get("user_id")}
    valid_oids = [ObjectId(uid) for uid in user_ids if ObjectId.is_valid(uid)]
    user_map = {str(u["_id"]): u.get("email", "Unknown") for u in db.users.find({"_id": {"$in": valid_oids}}, {"email": 1})}

    for cb in codebases:
        cb["user_email"] = user_map.get(cb.get("user_id"), "Unknown")

    return {
        "total": len(codebases),
        "codebases": codebases,
    }


@router.delete("/codebases/{codebase_id}")
def admin_delete_codebase(
    codebase_id: str,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Admin endpoint to delete any codebase and its associated data."""
    query = {"codebase_id": codebase_id}
    if ObjectId.is_valid(codebase_id):
        query = {"$or": [{"codebase_id": codebase_id}, {"_id": ObjectId(codebase_id)}]}
    codebase = db.codebases.find_one(query)
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")

    target_codebase_id = codebase.get("codebase_id") or str(codebase["_id"])
    chunks_result = db.code_chunks.delete_many({
        "$or": [{"codebase_id": target_codebase_id}, {"codebase_id": codebase_id}]
    })
    codebase_result = db.codebases.delete_one({"_id": codebase["_id"]})

    # Remove disk directory if exists
    for dir_id in [target_codebase_id, codebase_id]:
        codebase_dir = os.path.join(UPLOAD_DIR, dir_id)
        if os.path.exists(codebase_dir):
            shutil.rmtree(codebase_dir, ignore_errors=True)

    log_audit_event(
        user_id=str(admin["_id"]),
        email=admin["email"],
        action="ADMIN_CODEBASE_DELETED",
        resource_type="codebase",
        resource_id=codebase_id,
        details={
            "codebase_name": codebase.get("codebase_name"),
            "owner_user_id": codebase.get("user_id"),
        },
        ip_address=request.client.host if request.client else None,
    )

    return {
        "message": "Codebase deleted by administrator",
        "codebase_id": codebase_id,
        "deleted_codebases": codebase_result.deleted_count,
        "deleted_chunks": chunks_result.deleted_count,
    }
