"""Test suite for SaaS upgrades:
- Account profile update, password change, forgot/reset password, email verification
- Admin RBAC, admin stats, user management, audit logs
- Account deactivation & reactivation enforcement
- Multi-file upload and single-file instant analysis
- User stats aggregation
"""
import sys
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.database import db

client = TestClient(app)

def run_tests():
    print("========================================")
    print("Running SaaS Feature & Security Tests")
    print("========================================")

    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("PASS: API root is responsive")

    # 2. Create normal user
    uid = uuid.uuid4().hex[:6]
    user_email = f"saas_user_{uid}@example.com"
    user_pass = "UserPass123!"
    res = client.post("/auth/signup", json={"name": "SaaS Test User", "email": user_email, "password": user_pass})
    assert res.status_code == 201, f"Signup failed: {res.text}"
    print(f"PASS: User signup successful ({user_email})")

    # 3. Normal user login
    res = client.post("/auth/login", data={"username": user_email, "password": user_pass})
    assert res.status_code == 200, f"Login failed: {res.text}"
    user_token = res.json()["access_token"]
    user_auth = {"Authorization": f"Bearer {user_token}"}
    print("PASS: Normal user logged in")

    # 4. Check profile
    res = client.get("/auth/me", headers=user_auth)
    assert res.status_code == 200 and res.json()["email"] == user_email
    assert res.json()["role"] == "user"
    assert res.json()["is_active"] is True
    print("PASS: Profile retrieval verified")

    # 5. Update profile name
    res = client.put("/auth/profile", json={"name": "Updated SaaS Name"}, headers=user_auth)
    assert res.status_code == 200, f"Profile update failed: {res.text}"
    res = client.get("/auth/me", headers=user_auth)
    assert res.json()["name"] == "Updated SaaS Name"
    print("PASS: Profile update verified")

    # 6. Change password
    res = client.post("/auth/change-password", json={"old_password": user_pass, "new_password": "NewSecretPass456!"}, headers=user_auth)
    assert res.status_code == 200, f"Change password failed: {res.text}"
    # Verify login with new password
    res = client.post("/auth/login", data={"username": user_email, "password": "NewSecretPass456!"})
    assert res.status_code == 200
    user_token = res.json()["access_token"]
    user_auth = {"Authorization": f"Bearer {user_token}"}
    print("PASS: Password change verified")

    # 7. Forgot & Reset password flow
    res = client.post("/auth/forgot-password", json={"email": user_email})
    assert res.status_code == 200
    reset_token = res.json().get("dev_token")
    assert reset_token, "Expected dev_token for local test environment"
    res = client.post("/auth/reset-password", json={"token": reset_token, "new_password": "ResetPass789!"})
    assert res.status_code == 200, f"Reset password failed: {res.text}"
    # Login with reset password
    res = client.post("/auth/login", data={"username": user_email, "password": "ResetPass789!"})
    assert res.status_code == 200
    user_token = res.json()["access_token"]
    user_auth = {"Authorization": f"Bearer {user_token}"}
    print("PASS: Forgot and reset password flow verified")

    # 8. Email verification flow
    # 8a. Verify honest HTTP 503 when SMTP is not configured
    from datetime import datetime, timezone, timedelta
    from app.routes.auth import _hash_otp
    res = client.post("/auth/send-verification", headers=user_auth)
    assert res.status_code in (502, 503), f"Expected 502 or 503 when SMTP unconfigured or unreachable, got {res.status_code}"

    # 8b. Verify salted hash verification
    u_doc = db.users.find_one({"email": user_email})
    test_otp = "839201"
    otp_hash = _hash_otp(test_otp, str(u_doc["_id"]))
    db.users.update_one(
        {"_id": u_doc["_id"]},
        {"$set": {
            "verification_otp_hash": otp_hash,
            "verification_expires": datetime.now(timezone.utc) + timedelta(minutes=10),
            "verification_attempts": 0
        }}
    )
    res = client.post("/auth/verify-email", json={"otp": test_otp}, headers=user_auth)
    assert res.status_code == 200, f"Verification failed: {res.text}"
    res = client.get("/auth/me", headers=user_auth)
    assert res.json()["is_verified"] is True
    print("PASS: Email verification flow verified (Honest HTTP 503 & salted hash verification)")

    # 9. Verify normal user CANNOT access admin endpoints (RBAC test)
    res = client.get("/admin/stats", headers=user_auth)
    assert res.status_code == 403, f"Expected 403 Forbidden for user on /admin/stats, got {res.status_code}"
    res = client.get("/admin/users", headers=user_auth)
    assert res.status_code == 403, f"Expected 403 Forbidden for user on /admin/users, got {res.status_code}"
    print("PASS: Non-admin RBAC restriction verified (HTTP 403)")

    # 10. Create and promote an admin user
    admin_email = f"saas_admin_{uid}@example.com"
    admin_pass = "AdminPass123!"
    res = client.post("/auth/signup", json={"name": "System Admin", "email": admin_email, "password": admin_pass})
    assert res.status_code == 201
    # Promote admin in DB
    db.users.update_one({"email": admin_email}, {"$set": {"role": "admin"}})
    res = client.post("/auth/login", data={"username": admin_email, "password": admin_pass})
    assert res.status_code == 200
    admin_token = res.json()["access_token"]
    admin_auth = {"Authorization": f"Bearer {admin_token}"}
    print("PASS: Admin authenticated")

    # 11. Admin stats
    res = client.get("/admin/stats", headers=admin_auth)
    assert res.status_code == 200
    stats = res.json()
    assert "total_users" in stats and "total_codebases" in stats
    print(f"PASS: Admin stats retrieved ({stats['total_users']} users, {stats['total_codebases']} codebases)")

    # 12. Admin users list
    res = client.get("/admin/users", headers=admin_auth)
    assert res.status_code == 200
    users_data = res.json()
    assert users_data["total"] >= 2
    print("PASS: Admin users list retrieved")

    # 13. Admin deactivates normal user
    # Find normal user ID
    normal_user_doc = db.users.find_one({"email": user_email})
    normal_user_id = str(normal_user_doc["_id"])
    res = client.put(f"/admin/users/{normal_user_id}/status", json={"is_active": False}, headers=admin_auth)
    assert res.status_code == 200, f"Deactivate failed: {res.text}"

    # Verify deactivated user CANNOT login
    res = client.post("/auth/login", data={"username": user_email, "password": "ResetPass789!"})
    assert res.status_code == 403, f"Expected 403 for deactivated user login, got {res.status_code}"

    # Verify deactivated user token is rejected on protected routes
    res = client.get("/auth/me", headers=user_auth)
    assert res.status_code == 403, f"Expected 403 on protected route for deactivated user, got {res.status_code}"
    print("PASS: User deactivation enforced on login & protected routes (HTTP 403)")

    # 14. Admin reactivates normal user
    res = client.put(f"/admin/users/{normal_user_id}/status", json={"is_active": True}, headers=admin_auth)
    assert res.status_code == 200
    res = client.post("/auth/login", data={"username": user_email, "password": "ResetPass789!"})
    assert res.status_code == 200
    user_token = res.json()["access_token"]
    user_auth = {"Authorization": f"Bearer {user_token}"}
    print("PASS: User reactivation verified")

    # 15. Admin audit logs
    res = client.get("/admin/audit-logs", headers=admin_auth)
    assert res.status_code == 200
    logs = res.json()["audit_logs"]
    assert len(logs) > 0
    actions = [l["action"] for l in logs]
    assert "USER_DEACTIVATED" in actions and "USER_ACTIVATED" in actions
    print(f"PASS: Audit trail verified ({len(logs)} audit events)")

    # 16. Single file instant analysis
    sample_py = b'''"""Demo Module"""
import math

def calculate_area(radius: float) -> float:
    return math.pi * radius * radius

class CircleCalculator:
    def __init__(self, r: float):
        self.r = r
'''
    res = client.post(
        "/codebase/analyze-single-file",
        files={"file": ("calculator.py", sample_py, "text/x-python")},
        headers=user_auth
    )
    assert res.status_code == 200, f"Single file analysis failed: {res.text}"
    single_res = res.json()
    assert single_res["language"] == "python"
    assert single_res["summary"]["total_functions"] >= 1
    assert single_res["summary"]["total_classes"] >= 1
    print("PASS: Single file instant AST analysis verified")

    # 17. Multi-file upload
    file1 = ("main.py", b"def start():\n    return 'running'\n", "text/x-python")
    file2 = ("utils/helper.py", b"def add(a, b):\n    return a + b\n", "text/x-python")
    res = client.post(
        "/codebase/upload-files",
        files=[("files", file1), ("files", file2)],
        data={"codebase_name": "Multi-File Project"},
        headers=user_auth
    )
    assert res.status_code == 200, f"Multi-file upload failed: {res.text}"
    upload_res = res.json()
    created_cb_id = upload_res["codebase_id"]
    assert upload_res["total_files"] == 2
    print(f"PASS: Multi-file project upload verified (codebase_id: {created_cb_id})")

    # 18. User stats endpoint
    res = client.get("/codebase/stats", headers=user_auth)
    assert res.status_code == 200, f"User stats failed: {res.text}"
    user_stats = res.json()
    assert user_stats["total_codebases"] >= 1
    assert "Python" in user_stats["technologies"]
    print("PASS: User stats aggregation verified")

    # 19. Cleanup test data
    client.delete(f"/codebase/delete/{created_cb_id}", headers=user_auth)
    db.users.delete_many({"email": {"$in": [user_email, admin_email]}})
    print("PASS: Test cleanup completed successfully")

    print("========================================")
    print("ALL 19/19 SAAS BACKEND TESTS PASSED!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
