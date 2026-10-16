import io
import time
import uuid
import zipfile
from fastapi.testclient import TestClient

from app.main import app
from app.database import db

client = TestClient(app)

def test_full_e2e():
    print("==================================================")
    print("PHASE 5 — FULL END-TO-END VERIFICATION")
    print("==================================================")

    # 1. User Registration & Authentication
    tag = uuid.uuid4().hex[:6]
    email_alice = f"alice_{tag}@example.com"
    email_bob = f"bob_{tag}@example.com"
    pwd = "SecurePassword123!"

    print("[STEP 1] Registering Alice and Bob...")
    res_reg_a = client.post("/auth/signup", json={"name": "Alice Developer", "email": email_alice, "password": pwd})
    assert res_reg_a.status_code == 201, f"Signup Alice failed: {res_reg_a.text}"

    res_reg_b = client.post("/auth/signup", json={"name": "Bob Reviewer", "email": email_bob, "password": pwd})
    assert res_reg_b.status_code == 201, f"Signup Bob failed: {res_reg_b.text}"

    print("[STEP 2] Logging in Alice...")
    res_login_a = client.post("/auth/login", data={"username": email_alice, "password": pwd})
    assert res_login_a.status_code == 200, f"Login Alice failed: {res_login_a.text}"
    token_alice = res_login_a.json()["access_token"]
    headers_alice = {"Authorization": f"Bearer {token_alice}"}

    print("[STEP 3] Logging in Bob...")
    res_login_b = client.post("/auth/login", data={"username": email_bob, "password": pwd})
    assert res_login_b.status_code == 200, f"Login Bob failed: {res_login_b.text}"
    token_bob = res_login_b.json()["access_token"]
    headers_bob = {"Authorization": f"Bearer {token_bob}"}

    # 2. Profile Retrieval
    print("[STEP 4] Retrieving Alice's profile...")
    res_me = client.get("/auth/me", headers=headers_alice)
    assert res_me.status_code == 200, f"Profile failed: {res_me.text}"
    profile_alice = res_me.json()
    assert profile_alice["email"] == email_alice
    assert profile_alice["name"] == "Alice Developer"
    print(f" -> Alice User ID: {profile_alice['id']}")

    # 3. Create a comprehensive project repository
    print("[STEP 5] Preparing sample codebase ZIP...")
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("app/server.py", (
            "from fastapi import FastAPI, HTTPException\n"
            "from app.math_service import MathService\n\n"
            "app = FastAPI(title='Math API')\n"
            "math_svc = MathService()\n\n"
            "@app.get('/compute')\n"
            "def compute(x: int, y: int):\n"
            "    try:\n"
            "        val = math_svc.multiply(x, y)\n"
            "        return {'product': val}\n"
            "    except Exception:\n"
            "        raise HTTPException(status_code=500, detail='Math error')\n"
        ))
        zf.writestr("app/math_service.py", (
            "class MathService:\n"
            "    def multiply(self, a: int, b: int) -> int:\n"
            "        return a * b\n\n"
            "    def divide(self, a: int, b: int) -> float:\n"
            "        return a / b\n"
        ))
        zf.writestr("README.md", "# Math API Repository\nA microservice for arithmetic operations.\n")

    # 4. Upload ZIP by Alice
    print("[STEP 6] Uploading ZIP as Alice...")
    res_upload = client.post(
        "/codebase/upload",
        headers=headers_alice,
        files={"file": ("math_api.zip", zip_buf.getvalue(), "application/zip")}
    )
    assert res_upload.status_code == 200, f"Upload failed: {res_upload.text}"
    upload_res = res_upload.json()
    codebase_id = upload_res["codebase_id"]
    print(f" -> Upload succeeded! Codebase ID: {codebase_id}, files: {upload_res['total_files']}, chunks: {upload_res['total_chunks']}")

    try:
        # 5. Confirm MongoDB persistence
        print("[STEP 7] Checking MongoDB documents & chunk ownership...")
        cb = db.codebases.find_one({"codebase_id": codebase_id})
        assert cb is not None, "Codebase not found in MongoDB"
        assert cb["user_id"] == profile_alice["id"], "Codebase user_id does not match Alice"

        chunks = list(db.code_chunks.find({"codebase_id": codebase_id}))
        assert len(chunks) == upload_res["total_chunks"], "Chunk count mismatch in MongoDB"
        for ch in chunks:
            assert ch["user_id"] == profile_alice["id"], "Chunk user_id mismatch"
            assert ch["codebase_id"] == codebase_id, "Chunk codebase_id mismatch"
            assert len(ch["embedding"]) == 384, "Embedding dimensions mismatch"
        print(f" -> MongoDB persistence confirmed: {len(chunks)} chunks verified.")

        # 6. View codebase and its files
        print("[STEP 8] Querying codebase details, summary, and files...")
        res_details = client.get(f"/codebase/details/{codebase_id}", headers=headers_alice)
        assert res_details.status_code == 200
        assert res_details.json()["codebase_name"] == "math_api.zip"

        res_files = client.get(f"/codebase/files?codebase_id={codebase_id}", headers=headers_alice)
        assert res_files.status_code == 200
        relative_paths = [f["relative_path"] for f in res_files.json()["files"]]
        assert any("server.py" in p for p in relative_paths)

        res_summary = client.get(f"/codebase/summary?codebase_id={codebase_id}", headers=headers_alice)
        assert res_summary.status_code == 200

        res_tech = client.get(f"/codebase/technologies?codebase_id={codebase_id}", headers=headers_alice)
        assert res_tech.status_code == 200
        print(f" -> Files and metadata verified. Technologies detected: {[t['name'] for t in res_tech.json()['technologies']]}")

        # 7. Run AI features
        print("[STEP 9] Executing AI features...")

        # 7a. Explain file
        res_explain = client.get(f"/codebase/explain-file?codebase_id={codebase_id}&file_path=app/server.py", headers=headers_alice)
        assert res_explain.status_code == 200
        assert len(res_explain.json()["explanation"]) > 20
        print(" -> [AI] Explain file: OK")

        # 7b. Architecture overview
        res_arch = client.get(f"/codebase/architecture?codebase_id={codebase_id}", headers=headers_alice)
        assert res_arch.status_code == 200
        assert len(res_arch.json()["architecture_explanation"]) > 20
        print(" -> [AI] Architecture analysis: OK")

        # 7c. Semantic Code Search
        res_search = client.post("/codebase/search", headers=headers_alice, json={
            "query": "How is multiplication handled?",
            "codebase_id": codebase_id,
            "limit": 3
        })
        assert res_search.status_code == 200
        search_res = res_search.json()
        assert len(search_res["answer"]) > 10
        assert len(search_res["sources"]) > 0
        print(" -> [AI] Semantic Search: OK")

        # 7d. Issues detection
        res_issues = client.get(f"/codebase/issues?codebase_id={codebase_id}", headers=headers_alice)
        assert res_issues.status_code == 200
        issues_res = res_issues.json()
        assert issues_res["total_issues"] >= 1
        issue_item = issues_res["issues"][0]
        print(f" -> [AI] Issue Detector: OK (found {issues_res['total_issues']} issues: {issue_item['issue_type']} at line {issue_item['line_number']})")

        # 7e. Improvement suggestions
        res_impr = client.get(f"/codebase/improvements?codebase_id={codebase_id}", headers=headers_alice)
        assert res_impr.status_code == 200
        assert len(str(res_impr.json()["improvements"])) > 20
        print(" -> [AI] Code Improvements: OK")

        # 7f. Code fix
        res_fix = client.get(
            f"/codebase/fix?codebase_id={codebase_id}&file_path={issue_item['file_path']}&line_number={issue_item['line_number']}",
            headers=headers_alice
        )
        assert res_fix.status_code == 200
        assert len(res_fix.json()["suggested_fix"]) > 20
        print(" -> [AI] Code Fix Generator: OK")

        # 8. Cross-User Isolation (Bob cannot view, search, or delete Alice's codebase)
        print("[STEP 10] Verifying cross-user isolation for Bob...")
        assert client.get(f"/codebase/details/{codebase_id}", headers=headers_bob).status_code == 404
        assert client.get(f"/codebase/files?codebase_id={codebase_id}", headers=headers_bob).status_code == 404
        assert client.get(f"/codebase/architecture?codebase_id={codebase_id}", headers=headers_bob).status_code == 404
        assert client.post("/codebase/search", headers=headers_bob, json={"query": "test", "codebase_id": codebase_id}).status_code == 404
        assert client.delete(f"/codebase/delete/{codebase_id}", headers=headers_bob).status_code == 404
        print(" -> Cross-user isolation verified: Bob received 404 on all attempts.")

        # 9. Token Expiration and Missing Token Checks
        print("[STEP 11] Verifying missing & malformed token handling...")
        assert client.get(f"/codebase/details/{codebase_id}").status_code == 401
        assert client.get(f"/codebase/details/{codebase_id}", headers={"Authorization": "Bearer bad_token"}).status_code == 401
        print(" -> Missing/invalid token handling verified: returned 401.")

    finally:
        # 10. Clean up Alice's codebase and both test users
        print("[STEP 12] Cleaning up test data...")
        res_del = client.delete(f"/codebase/delete/{codebase_id}", headers=headers_alice)
        assert res_del.status_code == 200
        assert db.codebases.find_one({"codebase_id": codebase_id}) is None
        assert db.code_chunks.count_documents({"codebase_id": codebase_id}) == 0

        db.users.delete_many({"email": {"$in": [email_alice, email_bob]}})
        print(" -> Cleaned up test codebase and test users.")

    print("\n==================================================")
    print("ALL END-TO-END VERIFICATION STEPS PASSED (100%)")
    print("==================================================")

if __name__ == "__main__":
    test_full_e2e()
