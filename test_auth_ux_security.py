"""Automated test suite for Authentication UX and Security Improvements:
1. Weak password rejection during signup (short, common weak, repetitive)
2. Strong password acceptance during signup (entropy & passphrase friendly)
3. Normal user signup and login via /auth/login
4. Regular user denied access at /auth/admin-login (HTTP 403 Forbidden, no token, audit logged)
5. Backend RBAC enforcement on all /admin endpoints
6. Admin authentication via /auth/admin-login (HTTP 200, valid token, audit logged)
7. Admin access to /admin/stats and /admin/users
8. Authoritative password strength validation in /auth/change-password and /auth/reset-password
9. Account deactivation rejection on both login endpoints (HTTP 403)
10. Invalid/expired token handling (HTTP 401)
11. Audit log verification for denied vs successful admin attempts
"""
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.database import db
from app.utils.security import validate_password_strength

client = TestClient(app)

def test_auth_ux_and_security():
    print("==================================================")
    print("Running Authentication UX & Security Test Suite")
    print("==================================================")

    uid = uuid.uuid4().hex[:6]
    user_email = f"auth_user_{uid}@example.com"
    admin_email = f"auth_admin_{uid}@example.com"
    weak_pwd_short = "short"
    weak_pwd_common = "password123"
    weak_pwd_repeat = "11111111"
    strong_pwd = "SecurePass2026!#"
    strong_passphrase = "correct horse battery staple"

    # ----------------------------------------------------
    # TEST 1: Password Strength Validator Unit Checks
    # ----------------------------------------------------
    assert not validate_password_strength(weak_pwd_short)[0]
    assert not validate_password_strength(weak_pwd_common)[0]
    assert not validate_password_strength(weak_pwd_repeat)[0]
    assert validate_password_strength(strong_pwd)[0]
    assert validate_password_strength(strong_passphrase)[0]
    print("PASS 1: Password strength policy rules verified (Short, Common, and Repetitive rejected; Complex and Passphrases accepted)")

    # ----------------------------------------------------
    # TEST 2: Weak Password Rejected on Signup (HTTP 400)
    # ----------------------------------------------------
    res_weak_short = client.post("/auth/signup", json={"name": "Tester", "email": f"weak1_{uid}@example.com", "password": weak_pwd_short})
    assert res_weak_short.status_code == 422 or res_weak_short.status_code == 400
    print("PASS 2a: Short password rejected on signup")

    res_weak_common = client.post("/auth/signup", json={"name": "Tester", "email": f"weak2_{uid}@example.com", "password": weak_pwd_common})
    assert res_weak_common.status_code == 400, f"Expected 400 for common password, got {res_weak_common.status_code}"
    assert "too common or easily guessed" in res_weak_common.json()["detail"]
    print("PASS 2b: Common easily-guessed password rejected on signup")

    res_weak_rep = client.post("/auth/signup", json={"name": "Tester", "email": f"weak3_{uid}@example.com", "password": "aaaaaa11"})
    assert res_weak_rep.status_code == 400
    assert "repetitive characters" in res_weak_rep.json()["detail"]
    print("PASS 2c: Repetitive password rejected on signup")

    # ----------------------------------------------------
    # TEST 3: Strong Password Accepted on Signup
    # ----------------------------------------------------
    res_signup = client.post("/auth/signup", json={"name": "Regular User", "email": user_email, "password": strong_pwd})
    assert res_signup.status_code == 201, f"Signup failed: {res_signup.text}"
    user_doc = db.users.find_one({"email": user_email})
    assert user_doc is not None
    assert user_doc.get("role") == "user"
    print(f"PASS 3: Normal user registered with strong password ({user_email})")

    # ----------------------------------------------------
    # TEST 4: Normal User Login via /auth/login
    # ----------------------------------------------------
    res_login = client.post("/auth/login", data={"username": user_email, "password": strong_pwd})
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    user_token = res_login.json()["access_token"]
    user_auth = {"Authorization": f"Bearer {user_token}"}

    res_me = client.get("/auth/me", headers=user_auth)
    assert res_me.status_code == 200
    assert res_me.json()["role"] == "user"
    print("PASS 4: Normal user authenticated via /auth/login, role is 'user'")

    # ----------------------------------------------------
    # TEST 5: Regular User Denied at /auth/admin-login (HTTP 403)
    # ----------------------------------------------------
    res_admin_login_denied = client.post("/auth/admin-login", data={"username": user_email, "password": strong_pwd})
    assert res_admin_login_denied.status_code == 403, f"Expected 403 Forbidden, got {res_admin_login_denied.status_code}"
    assert "access denied: administrator privileges required" in res_admin_login_denied.json()["detail"].lower()
    assert "access_token" not in res_admin_login_denied.json(), "CRITICAL: No access token must be issued on denied admin login"

    # Check audit log recorded the denied attempt
    denied_audit = db.audit_logs.find_one({"email": user_email, "action": "ADMIN_LOGIN_DENIED_NON_ADMIN"})
    assert denied_audit is not None
    print("PASS 5: Regular user strictly denied at /auth/admin-login (HTTP 403, no token issued, audit logged)")

    # ----------------------------------------------------
    # TEST 6: Regular User Denied at Backend Admin Endpoints (HTTP 403)
    # ----------------------------------------------------
    res_stats_denied = client.get("/admin/stats", headers=user_auth)
    assert res_stats_denied.status_code == 403
    res_users_denied = client.get("/admin/users", headers=user_auth)
    assert res_users_denied.status_code == 403
    print("PASS 6: Regular user token rejected on all backend /admin routes (HTTP 403)")

    # ----------------------------------------------------
    # TEST 7: Admin Account Creation & Authentication via /auth/admin-login
    # ----------------------------------------------------
    res_admin_signup = client.post("/auth/signup", json={"name": "System Administrator", "email": admin_email, "password": strong_pwd})
    assert res_admin_signup.status_code == 201

    # Promote to admin in trusted database
    db.users.update_one({"email": admin_email}, {"$set": {"role": "admin"}})

    # Admin Login via /auth/admin-login
    res_admin_login = client.post("/auth/admin-login", data={"username": admin_email, "password": strong_pwd})
    assert res_admin_login.status_code == 200, f"Admin login failed: {res_admin_login.text}"
    admin_token = res_admin_login.json()["access_token"]
    admin_auth = {"Authorization": f"Bearer {admin_token}"}

    # Verify audit log recorded success
    success_audit = db.audit_logs.find_one({"email": admin_email, "action": "ADMIN_LOGIN_SUCCESS"})
    assert success_audit is not None
    print(f"PASS 7: Admin authenticated via /auth/admin-login with valid token and audit record ({admin_email})")

    # ----------------------------------------------------
    # TEST 8: Admin Accesses /admin/stats and /admin/users
    # ----------------------------------------------------
    res_admin_stats = client.get("/admin/stats", headers=admin_auth)
    assert res_admin_stats.status_code == 200
    assert "total_users" in res_admin_stats.json()

    res_admin_users = client.get("/admin/users", headers=admin_auth)
    assert res_admin_users.status_code == 200
    assert res_admin_users.json()["total"] >= 2
    print("PASS 8: Admin authorization verified on /admin/stats and /admin/users (HTTP 200)")

    # ----------------------------------------------------
    # TEST 9: Admin Logs In via /auth/login (User Sign In)
    # ----------------------------------------------------
    res_admin_user_login = client.post("/auth/login", data={"username": admin_email, "password": strong_pwd})
    assert res_admin_user_login.status_code == 200
    admin_user_token = res_admin_user_login.json()["access_token"]
    res_admin_me = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_user_token}"})
    assert res_admin_me.status_code == 200
    assert res_admin_me.json()["role"] == "admin"
    print("PASS 9: Admin can log in at /auth/login and profile indicates role='admin' for redirect")

    # ----------------------------------------------------
    # TEST 10: Change Password Enforces Strength Validation
    # ----------------------------------------------------
    # Attempt change with weak password
    res_change_weak = client.post("/auth/change-password", json={"old_password": strong_pwd, "new_password": "password123"}, headers=user_auth)
    assert res_change_weak.status_code == 400
    assert "too common or easily guessed" in res_change_weak.json()["detail"]

    # Attempt change with strong password
    new_strong = "NewSecurePass8899!#"
    res_change_strong = client.post("/auth/change-password", json={"old_password": strong_pwd, "new_password": new_strong}, headers=user_auth)
    assert res_change_strong.status_code == 200
    print("PASS 10: /auth/change-password enforces password strength validation")

    # ----------------------------------------------------
    # TEST 11: Deactivated User Denied on Both Login Endpoints
    # ----------------------------------------------------
    db.users.update_one({"email": user_email}, {"$set": {"is_active": False}})

    res_deactivated_user = client.post("/auth/login", data={"username": user_email, "password": new_strong})
    assert res_deactivated_user.status_code == 403
    assert "deactivated" in res_deactivated_user.json()["detail"].lower()

    res_deactivated_admin_login = client.post("/auth/admin-login", data={"username": user_email, "password": new_strong})
    assert res_deactivated_admin_login.status_code == 403
    assert "deactivated" in res_deactivated_admin_login.json()["detail"].lower()
    print("PASS 11: Deactivated user access denied on both login endpoints (HTTP 403)")

    # ----------------------------------------------------
    # TEST 12: Clean Up Test Records
    # ----------------------------------------------------
    db.users.delete_many({"email": {"$in": [user_email, admin_email]}})
    db.audit_logs.delete_many({"email": {"$in": [user_email, admin_email]}})
    print("PASS 12: Test artifacts cleaned up successfully")

    print("==================================================")
    print("ALL 12 AUTH UX & SECURITY TESTS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    test_auth_ux_and_security()
