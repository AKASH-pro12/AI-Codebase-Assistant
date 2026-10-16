import io
import sys
import uuid
import zipfile
from fastapi.testclient import TestClient

from app.main import app
from app.database import db

client = TestClient(app)

def run_tests():
    print("=== STARTING BACKEND TEST SUITE ===")
    
    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("[PASS] 1. Root / health check passed")

    # 2. Unauthenticated checks
    res = client.get("/auth/me")
    assert res.status_code == 401, f"Expected 401 on /auth/me without token, got {res.status_code}"
    assert res.json().get("detail") == "Not authenticated"
    print("[PASS] 2. GET /auth/me returns 401 Not authenticated without token")

    res = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token_12345"})
    assert res.status_code == 401, f"Expected 401 on /auth/me with invalid token, got {res.status_code}"
    print("[PASS] 3. GET /auth/me returns 401 with invalid token")

    res = client.post("/codebase/upload")
    assert res.status_code == 401, f"Expected 401 on /codebase/upload without token, got {res.status_code}"
    print("[PASS] 4. POST /codebase/upload returns 401 without token")

    res = client.post("/codebase/upload", headers={"Authorization": "Bearer bad_token"})
    assert res.status_code == 401, f"Expected 401 on /codebase/upload with invalid token, got {res.status_code}"
    print("[PASS] 5. POST /codebase/upload returns 401 with invalid token")

    # 3. User setup: User A and User B
    uid_suffix = uuid.uuid4().hex[:6]
    user_a_email = f"test_a_{uid_suffix}@example.com"
    user_b_email = f"test_b_{uid_suffix}@example.com"
    password = "TestPassword123!"

    # Signup User A
    res = client.post("/auth/signup", json={"name": "User A", "email": user_a_email, "password": password})
    assert res.status_code == 201, f"Signup A failed: {res.text}"
    print(f"[PASS] 6. Signup User A ({user_a_email}) succeeded")

    # Signup User B
    res = client.post("/auth/signup", json={"name": "User B", "email": user_b_email, "password": password})
    assert res.status_code == 201, f"Signup B failed: {res.text}"
    print(f"[PASS] 7. Signup User B ({user_b_email}) succeeded")

    # Login User A
    res = client.post("/auth/login", data={"username": user_a_email, "password": password})
    assert res.status_code == 200, f"Login A failed: {res.text}"
    token_a = res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("[PASS] 8. Login User A succeeded, access token obtained")

    # Login User B
    res = client.post("/auth/login", data={"username": user_b_email, "password": password})
    assert res.status_code == 200, f"Login B failed: {res.text}"
    token_b = res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print("[PASS] 9. Login User B succeeded, access token obtained")

    # Verify Profile A
    res = client.get("/auth/me", headers=headers_a)
    assert res.status_code == 200, f"Profile A failed: {res.text}"
    profile_a = res.json()
    assert profile_a["email"] == user_a_email
    print(f"[PASS] 10. GET /auth/me returns profile for User A (ID: {profile_a['id']})")

    # 4. Upload validation checks for User A
    # Non-zip upload
    res = client.post(
        "/codebase/upload",
        headers=headers_a,
        files={"file": ("test.txt", b"some text", "text/plain")}
    )
    assert res.status_code == 400, f"Expected 400 for non-zip file, got {res.status_code}"
    print("[PASS] 11. Reject non-zip upload with 400")

    # Empty zip file upload
    res = client.post(
        "/codebase/upload",
        headers=headers_a,
        files={"file": ("empty.zip", b"", "application/zip")}
    )
    assert res.status_code == 400, f"Expected 400 for empty zip file, got {res.status_code}"
    print("[PASS] 12. Reject 0-byte zip file with 400")

    # Zip with no supported source code files
    unsupported_buf = io.BytesIO()
    with zipfile.ZipFile(unsupported_buf, "w") as zf:
        zf.writestr("image.png", b"\x89PNG\r\n\x1a\n")
    res = client.post(
        "/codebase/upload",
        headers=headers_a,
        files={"file": ("unsupported.zip", unsupported_buf.getvalue(), "application/zip")}
    )
    assert res.status_code == 400, f"Expected 400 for unsupported code files, got {res.status_code}: {res.text}"
    print("[PASS] 13. Reject zip with no supported code files with 400")

    # Zip with path traversal
    traversal_buf = io.BytesIO()
    with zipfile.ZipFile(traversal_buf, "w") as zf:
        zf.writestr("../../evil.py", b"print('exploit')\n")
    res = client.post(
        "/codebase/upload",
        headers=headers_a,
        files={"file": ("traversal.zip", traversal_buf.getvalue(), "application/zip")}
    )
    assert res.status_code == 400, f"Expected 400 for path traversal, got {res.status_code}: {res.text}"
    print("[PASS] 14. Reject path traversal zip with 400")

    # 5. Valid Zip Upload
    valid_buf = io.BytesIO()
    with zipfile.ZipFile(valid_buf, "w") as zf:
        zf.writestr("main.py", (
            "import os\n\n"
            "def calculate_total(prices: list[float]) -> float:\n"
            "    total = 0.0\n"
            "    for p in prices:\n"
            "        total += p\n"
            "    return total\n"
        ))
        zf.writestr("utils.py", (
            "class MathHelper:\n"
            "    def multiply(self, a: int, b: int) -> int:\n"
            "        return a * b\n"
        ))
        zf.writestr("README.md", "# Test Project\nA sample project for verification.")
    valid_bytes = valid_buf.getvalue()

    res = client.post(
        "/codebase/upload",
        headers=headers_a,
        files={"file": ("sample_repo.zip", valid_bytes, "application/zip")}
    )
    assert res.status_code == 200, f"Valid upload failed: {res.status_code}: {res.text}"
    upload_data = res.json()
    codebase_id = upload_data.get("codebase_id")
    assert codebase_id, "Missing codebase_id in upload response"
    print(f"[PASS] 15. Valid upload succeeded! Codebase ID: {codebase_id}, files: {upload_data.get('total_files')}, chunks: {upload_data.get('total_chunks')}")

    # 6. Verify MongoDB persistence & ownership integrity
    cb_doc = db.codebases.find_one({"codebase_id": codebase_id})
    assert cb_doc is not None, "Codebase document not found in MongoDB"
    assert cb_doc["user_id"] == profile_a["id"], f"Codebase user_id mismatch: {cb_doc['user_id']} vs {profile_a['id']}"
    assert cb_doc["total_files"] == 3

    chunks = list(db.code_chunks.find({"codebase_id": codebase_id}))
    assert len(chunks) > 0, "No chunks found in MongoDB for uploaded codebase"
    for chunk in chunks:
        assert chunk["user_id"] == profile_a["id"], "Chunk user_id mismatch"
        assert chunk["codebase_id"] == codebase_id, "Chunk codebase_id mismatch"
        assert len(chunk["embedding"]) == 384, f"Chunk embedding dimension expected 384, got {len(chunk['embedding'])}"
    print(f"[PASS] 16. MongoDB persistence verified: {len(chunks)} chunks, all tagged with user_id={profile_a['id']}")

    # 7. Repository endpoints for User A
    res = client.get("/codebase/list", headers=headers_a)
    assert res.status_code == 200
    listed_ids = [c["codebase_id"] for c in res.json()["codebases"]]
    assert codebase_id in listed_ids, "Uploaded codebase not in user A's list"
    print("[PASS] 17. GET /codebase/list includes uploaded codebase for User A")

    res = client.get(f"/codebase/details/{codebase_id}", headers=headers_a)
    assert res.status_code == 200
    assert res.json()["codebase_id"] == codebase_id
    print("[PASS] 18. GET /codebase/details/{codebase_id} succeeded")

    res = client.get(f"/codebase/files?codebase_id={codebase_id}", headers=headers_a)
    assert res.status_code == 200
    file_paths = [f["relative_path"] for f in res.json()["files"]]
    assert "main.py" in file_paths and "utils.py" in file_paths
    print(f"[PASS] 19. GET /codebase/files returned: {file_paths}")

    res = client.get(f"/codebase/summary?codebase_id={codebase_id}", headers=headers_a)
    assert res.status_code == 200
    print("[PASS] 20. GET /codebase/summary succeeded")

    res = client.get(f"/codebase/technologies?codebase_id={codebase_id}", headers=headers_a)
    assert res.status_code == 200
    print(f"[PASS] 21. GET /codebase/technologies succeeded: {[t['name'] for t in res.json()['technologies']]}")

    res = client.get(f"/codebase/file?codebase_id={codebase_id}&file_path=main.py", headers=headers_a)
    assert res.status_code == 200
    assert "calculate_total" in res.json()["content"]
    print("[PASS] 22. GET /codebase/file returned file content")

    # 8. Cross-User Isolation (User B must NOT be able to access or delete User A's codebase)
    res = client.get(f"/codebase/details/{codebase_id}", headers=headers_b)
    assert res.status_code == 404, f"Expected 404 for User B accessing User A's codebase, got {res.status_code}"
    print("[PASS] 23. Cross-user isolation: User B cannot view User A's codebase details (404)")

    res = client.get(f"/codebase/files?codebase_id={codebase_id}", headers=headers_b)
    assert res.status_code == 404, f"Expected 404 for User B accessing User A's codebase files, got {res.status_code}"
    print("[PASS] 24. Cross-user isolation: User B cannot view User A's codebase files (404)")

    res = client.delete(f"/codebase/delete/{codebase_id}", headers=headers_b)
    assert res.status_code == 404, f"Expected 404 for User B deleting User A's codebase, got {res.status_code}"
    print("[PASS] 25. Cross-user isolation: User B cannot delete User A's codebase (404)")

    # 9. Clean up test codebase via User A
    res = client.delete(f"/codebase/delete/{codebase_id}", headers=headers_a)
    assert res.status_code == 200, f"Delete failed: {res.text}"
    assert res.json()["deleted_codebase_documents"] == 1
    assert res.json()["deleted_chunks"] == len(chunks)
    assert db.codebases.find_one({"codebase_id": codebase_id}) is None
    assert db.code_chunks.count_documents({"codebase_id": codebase_id}) == 0
    print(f"[PASS] 26. User A deleted codebase cleanly (0 chunks or records orphaned)")

    # Clean up test users from DB
    db.users.delete_many({"_id": {"$in": [db.users.find_one({"email": user_a_email})["_id"], db.users.find_one({"email": user_b_email})["_id"]]}})
    print("[PASS] 27. Cleaned up temporary test users")

    print("\n=== ALL PHASE 1 & 2 TESTS PASSED PERFECTLY ===")

if __name__ == "__main__":
    run_tests()
