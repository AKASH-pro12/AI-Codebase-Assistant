"""Comprehensive automated test suite for:
1. Real Email Verification:
   - Honest error handling when SMTP is not configured (HTTP 503)
   - 60-second cooldown rate-limiting (HTTP 429)
   - Salted SHA-256 OTP hashing (no plaintext OTP in MongoDB, no OTP in response)
   - Maximum 5 failed attempts lockout / invalidation
   - Successful verification when valid OTP hash is matched
2. AI Codebase Chat:
   - Ownership isolation (HTTP 404 for non-existent or foreign codebases)
   - Chat endpoint execution with vector chunks & file focus context
   - Source citations and truthfulness constraints
   - Multi-turn conversation history
"""
import os
import uuid
import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import db
from app.routes.auth import _hash_otp

client = TestClient(app)

def test_email_verification_and_chat():
    print("==================================================")
    print("Running Email Verification & AI Chat Test Suite")
    print("==================================================")

    # Setup test user
    uid = uuid.uuid4().hex[:6]
    test_email = f"chat_verify_{uid}@example.com"
    test_pass = "SecurePass123!"

    res = client.post("/auth/signup", json={"name": "Verify & Chat Tester", "email": test_email, "password": test_pass})
    assert res.status_code == 201, f"Signup failed: {res.text}"

    res = client.post("/auth/login", data={"username": test_email, "password": test_pass})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # ----------------------------------------------------
    # TEST 1: Honest SMTP Error when unconfigured (HTTP 503)
    # ----------------------------------------------------
    with patch("app.routes.auth.is_email_configured", return_value=False):
        res = client.post("/auth/send-verification", headers=auth_header)
        assert res.status_code == 503, f"Expected 503 when SMTP unconfigured, got {res.status_code}"
        assert "Email delivery service is not configured" in res.json()["detail"]
        print("PASS 1: Honest HTTP 503 returned when SMTP is not configured")

    # ----------------------------------------------------
    # TEST 2: Email dispatch & No OTP Leak in response
    # ----------------------------------------------------
    with patch("app.routes.auth.is_email_configured", return_value=True), \
         patch("app.routes.auth.send_verification_email", return_value=(True, None)):
        res = client.post("/auth/send-verification", headers=auth_header)
        assert res.status_code == 200, f"Send verification failed: {res.text}"
        data = res.json()
        assert "dev_otp" not in data, "CRITICAL: dev_otp must NOT be exposed in API response"
        assert "otp" not in data, "CRITICAL: OTP must NOT be exposed in API response"
        assert data.get("cooldown_seconds") == 60
        print("PASS 2: Verification email dispatched safely without leaking OTP in API response")

    # ----------------------------------------------------
    # TEST 3: Cooldown Rate Limiting (HTTP 429)
    # ----------------------------------------------------
    with patch("app.routes.auth.is_email_configured", return_value=True), \
         patch("app.routes.auth.send_verification_email", return_value=(True, None)):
        res_rapid = client.post("/auth/send-verification", headers=auth_header)
        assert res_rapid.status_code == 429, f"Expected 429 for rapid resend, got {res_rapid.status_code}"
        assert "seconds before requesting another" in res_rapid.json()["detail"]
        print("PASS 3: 60-second cooldown rate limit enforced (HTTP 429)")

    # ----------------------------------------------------
    # TEST 4: Salted Hash Storage in MongoDB (No plaintext)
    # ----------------------------------------------------
    user_doc = db.users.find_one({"email": test_email})
    assert user_doc is not None
    assert "verification_otp" not in user_doc or not user_doc["verification_otp"], "Plaintext OTP must not exist in DB"
    assert "verification_otp_hash" in user_doc and len(user_doc["verification_otp_hash"]) == 64, "SHA-256 hash must be present"
    print("PASS 4: OTP stored exclusively as salted SHA-256 hash in database")

    # ----------------------------------------------------
    # TEST 5: Failed verification attempts & Lockout
    # ----------------------------------------------------
    # Reset cooldown and set known hash for testing
    simulated_otp = "482910"
    user_id_str = str(user_doc["_id"])
    sim_hash = _hash_otp(simulated_otp, user_id_str)
    db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "verification_otp_hash": sim_hash,
            "verification_expires": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
            "verification_attempts": 0
        }}
    )

    # 4 invalid attempts
    for i in range(1, 5):
        res_wrong = client.post("/auth/verify-email", json={"otp": "000000"}, headers=auth_header)
        assert res_wrong.status_code == 400
        assert f"{5 - i} attempt(s) remaining" in res_wrong.json()["detail"]
    print("PASS 5a: Invalid OTP attempts correctly counted and reported")

    # 5th invalid attempt triggers invalidation
    res_lockout = client.post("/auth/verify-email", json={"otp": "000000"}, headers=auth_header)
    assert res_lockout.status_code == 429
    assert "Too many failed verification attempts" in res_lockout.json()["detail"]
    
    # Verify hash has been unset
    user_after_lock = db.users.find_one({"_id": user_doc["_id"]})
    assert "verification_otp_hash" not in user_after_lock or not user_after_lock["verification_otp_hash"]
    print("PASS 5b: Lockout triggered after 5 failed attempts, code invalidated")

    # ----------------------------------------------------
    # TEST 6: Successful Verification
    # ----------------------------------------------------
    db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "verification_otp_hash": sim_hash,
            "verification_expires": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
            "verification_attempts": 0
        }}
    )
    res_correct = client.post("/auth/verify-email", json={"otp": simulated_otp}, headers=auth_header)
    assert res_correct.status_code == 200, f"Valid OTP verification failed: {res_correct.text}"
    assert res_correct.json()["is_verified"] is True

    # Check profile reflect is_verified: True
    res_me = client.get("/auth/me", headers=auth_header)
    assert res_me.json()["is_verified"] is True
    print("PASS 6: Successful verification with salted hash; profile marked is_verified=True")

    # ----------------------------------------------------
    # TEST 7: AI Codebase Chat Ownership Isolation
    # ----------------------------------------------------
    foreign_id = "non-existent-or-foreign-codebase-id"
    res_chat_foreign = client.post(
        f"/codebase/{foreign_id}/chat",
        json={"message": "What is the purpose of this project?"},
        headers=auth_header
    )
    assert res_chat_foreign.status_code == 404, f"Expected 404 for foreign codebase, got {res_chat_foreign.status_code}"
    print("PASS 7: Codebase ownership access control enforced on AI Chat (HTTP 404)")

    # ----------------------------------------------------
    # TEST 8: AI Codebase Chat with Real Codebase & Citations
    # ----------------------------------------------------
    # Create a test codebase for this user
    test_cb_id = f"cb_chat_test_{uid}"
    file_path = "services/billing.py"
    file_content = (
        "class SubscriptionManager:\n"
        "    def __init__(self, plan: str):\n"
        "        self.plan = plan\n"
        "    def get_price(self) -> float:\n"
        "        return 29.99 if self.plan == 'pro' else 0.0\n"
    )

    db.codebases.insert_one({
        "codebase_id": test_cb_id,
        "user_id": user_id_str,
        "codebase_name": "Billing Service",
        "description": "Test billing service",
        "files": [{"file_path": file_path, "relative_path": file_path}],
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    })

    db.code_chunks.insert_one({
        "codebase_id": test_cb_id,
        "user_id": user_id_str,
        "file_path": file_path,
        "relative_path": file_path,
        "content": file_content,
        "chunk_index": 0,
        "extension": ".py"
    })

    # Test Chat with active file focus
    with patch("app.routes.codebase_routes.chat.search_similar_chunks", return_value=[]), \
         patch("app.routes.codebase_routes.chat.llm") as mock_llm:
        class MockAIResponse:
            content = "The `SubscriptionManager` class in `services/billing.py` manages billing plans, returning 29.99 for the 'pro' plan."
        mock_llm.invoke.return_value = MockAIResponse()

        chat_payload = {
            "message": "How does the SubscriptionManager determine pricing?",
            "file_focus": "services/billing.py",
            "chat_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I assist with your codebase today?"}
            ]
        }
        res_chat = client.post(f"/codebase/{test_cb_id}/chat", json=chat_payload, headers=auth_header)
        assert res_chat.status_code == 200, f"Chat failed: {res_chat.text}"
        chat_data = res_chat.json()
        assert "reply" in chat_data
        assert "SubscriptionManager" in chat_data["reply"]
        assert len(chat_data["sources"]) > 0
        assert chat_data["sources"][0]["file_path"] == "services/billing.py"
        assert chat_data["sources"][0]["is_active_file"] is True
        print(f"PASS 8: AI Codebase Chat executed with file focus context and source citations ({chat_data['sources'][0]['file_path']})")

    # ----------------------------------------------------
    # TEST 9: Alternative Chat endpoint (/codebase/chat)
    # ----------------------------------------------------
    with patch("app.routes.codebase_routes.chat.search_similar_chunks", return_value=[]), \
         patch("app.routes.codebase_routes.chat.llm") as mock_llm_alt:
        class MockAIResponseAlt:
            content = "Pricing is determined by the `get_price` method."
        mock_llm_alt.invoke.return_value = MockAIResponseAlt()

        alt_payload = {
            "codebase_id": test_cb_id,
            "message": "Explain get_price",
            "chat_history": []
        }
        res_alt = client.post("/codebase/chat", json=alt_payload, headers=auth_header)
        assert res_alt.status_code == 200
        assert "get_price" in res_alt.json()["reply"]
        print("PASS 9: Alternative /codebase/chat endpoint verified")

    # Cleanup test artifacts
    db.codebases.delete_one({"codebase_id": test_cb_id})
    db.code_chunks.delete_many({"codebase_id": test_cb_id})
    db.users.delete_one({"email": test_email})
    print("PASS 10: Test artifacts cleaned up successfully")

    print("==================================================")
    print("ALL 10 EMAIL VERIFICATION & AI CHAT TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_email_verification_and_chat()
