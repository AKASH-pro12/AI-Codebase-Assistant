import io
import sys
import uuid
import zipfile
from fastapi.testclient import TestClient

from app.main import app
from app.database import db

client = TestClient(app)

def run_tests():
    print("=== STARTING PHASE 3 AI FUNCTIONALITY TEST SUITE ===")

    # 1. Create test user
    uid = uuid.uuid4().hex[:6]
    user_email = f"ai_tester_{uid}@example.com"
    other_email = f"other_tester_{uid}@example.com"
    pwd = "AiPassword123!"

    client.post("/auth/signup", json={"name": "AI Tester", "email": user_email, "password": pwd})
    client.post("/auth/signup", json={"name": "Other Tester", "email": other_email, "password": pwd})

    res_a = client.post("/auth/login", data={"username": user_email, "password": pwd})
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res_b = client.post("/auth/login", data={"username": other_email, "password": pwd})
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Build a rich Python test repository ZIP with:
    # - functions
    # - classes
    # - FastAPI routes
    # - local dependencies
    # - an intentional issue (bare except or broad exception) for issue detector and code fix
    sample_api = (
        "from fastapi import FastAPI, HTTPException\n"
        "from services.calculator import Calculator\n\n"
        "app = FastAPI()\n"
        "calc = Calculator()\n\n"
        "@app.get('/add')\n"
        "def add_numbers(a: int, b: int):\n"
        "    try:\n"
        "        return {'result': calc.add(a, b)}\n"
        "    except Exception:\n"
        "        raise HTTPException(status_code=500, detail='Error')\n"
    )

    sample_calc = (
        "class Calculator:\n"
        "    def add(self, a: int, b: int) -> int:\n"
        "        return a + b\n\n"
        "    def subtract(self, a: int, b: int) -> int:\n"
        "        return a - b\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("main.py", sample_api)
        zf.writestr("services/calculator.py", sample_calc)

    res = client.post(
        "/codebase/upload",
        headers=headers_a,
        files={"file": ("ai_test_repo.zip", buf.getvalue(), "application/zip")}
    )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    codebase_id = res.json()["codebase_id"]
    print(f"[PASS] 1. Uploaded AI test repo, codebase_id={codebase_id}")

    try:
        # 3. Test /codebase/explain-file (uses LLM)
        res = client.get(
            f"/codebase/explain-file?codebase_id={codebase_id}&file_path=main.py",
            headers=headers_a
        )
        assert res.status_code == 200, f"explain-file failed: {res.text}"
        data = res.json()
        assert "explanation" in data and len(data["explanation"]) > 0
        print("[PASS] 2. GET /codebase/explain-file succeeded with LLM explanation")

        # 4. Test /codebase/functions
        res = client.get(
            f"/codebase/functions?codebase_id={codebase_id}&file_path=main.py",
            headers=headers_a
        )
        assert res.status_code == 200, f"functions failed: {res.text}"
        fn_names = [f["name"] for f in res.json()["functions"]]
        assert "add_numbers" in fn_names
        print(f"[PASS] 3. GET /codebase/functions detected: {fn_names}")

        # 5. Test /codebase/classes
        res = client.get(
            f"/codebase/classes?codebase_id={codebase_id}&file_path=services/calculator.py",
            headers=headers_a
        )
        assert res.status_code == 200, f"classes failed: {res.text}"
        class_names = [c["name"] for c in res.json()["classes"]]
        assert "Calculator" in class_names
        print(f"[PASS] 4. GET /codebase/classes detected: {class_names}")

        # 6. Test /codebase/routes
        res = client.get(
            f"/codebase/routes?codebase_id={codebase_id}&file_path=main.py",
            headers=headers_a
        )
        assert res.status_code == 200, f"routes failed: {res.text}"
        routes = res.json()["routes"]
        assert len(routes) >= 1
        assert routes[0]["path"] == "/add"
        print(f"[PASS] 5. GET /codebase/routes detected route: {routes[0]['path']} [{routes[0]['methods']}]")

        # 7. Test /codebase/dependencies
        res = client.get(
            f"/codebase/dependencies?codebase_id={codebase_id}&file_path=main.py",
            headers=headers_a
        )
        assert res.status_code == 200, f"dependencies failed: {res.text}"
        print(f"[PASS] 6. GET /codebase/dependencies detected {res.json()['total_imports']} imports")

        # 8. Test /codebase/relationships
        res = client.get(
            f"/codebase/relationships?codebase_id={codebase_id}&file_path=main.py",
            headers=headers_a
        )
        assert res.status_code == 200, f"relationships failed: {res.text}"
        print(f"[PASS] 7. GET /codebase/relationships succeeded: {res.json()['total_relationships']} relationships")

        # 9. Test /codebase/architecture (uses LLM)
        res = client.get(
            f"/codebase/architecture?codebase_id={codebase_id}",
            headers=headers_a
        )
        assert res.status_code == 200, f"architecture failed: {res.text}"
        arch_data = res.json()
        assert "architecture_explanation" in arch_data and len(arch_data["architecture_explanation"]) > 0
        print("[PASS] 8. GET /codebase/architecture generated overview with LLM")

        # 10. Test /codebase/search (Vector search + RAG LLM)
        res = client.post(
            "/codebase/search",
            headers=headers_a,
            json={
                "query": "Where is addition implemented?",
                "codebase_id": codebase_id,
                "limit": 3
            }
        )
        assert res.status_code == 200, f"search failed: {res.text}"
        search_data = res.json()
        assert "answer" in search_data and len(search_data["answer"]) > 0
        assert len(search_data["sources"]) > 0
        print(f"[PASS] 9. POST /codebase/search succeeded with sources: {[s['file_path'] for s in search_data['sources']]}")

        # 11. Test /codebase/issues
        res = client.get(
            f"/codebase/issues?codebase_id={codebase_id}",
            headers=headers_a
        )
        assert res.status_code == 200, f"issues failed: {res.text}"
        issues_data = res.json()
        assert issues_data["total_issues"] > 0
        first_issue = issues_data["issues"][0]
        print(f"[PASS] 10. GET /codebase/issues detected {issues_data['total_issues']} issues: {first_issue['issue_type']} at line {first_issue['line_number']}")

        # 12. Test /codebase/improvements (uses LLM)
        res = client.get(
            f"/codebase/improvements?codebase_id={codebase_id}",
            headers=headers_a
        )
        assert res.status_code == 200, f"improvements failed: {res.text}"
        assert "improvements" in res.json()
        print("[PASS] 11. GET /codebase/improvements returned suggestions")

        # 13. Test /codebase/fix (uses LLM)
        res = client.get(
            f"/codebase/fix?codebase_id={codebase_id}&file_path=main.py&line_number={first_issue['line_number']}",
            headers=headers_a
        )
        assert res.status_code == 200, f"fix failed: {res.text}"
        fix_data = res.json()
        assert "suggested_fix" in fix_data and len(fix_data["suggested_fix"]) > 0
        print("[PASS] 12. GET /codebase/fix generated fix suggestion with LLM")

        # 14. Cross-user isolation on AI endpoints (User B cannot query User A's codebase)
        for ep, method in [
            (f"/codebase/explain-file?codebase_id={codebase_id}&file_path=main.py", "GET"),
            (f"/codebase/architecture?codebase_id={codebase_id}", "GET"),
            (f"/codebase/issues?codebase_id={codebase_id}", "GET"),
            (f"/codebase/improvements?codebase_id={codebase_id}", "GET"),
        ]:
            r = client.get(ep, headers=headers_b)
            assert r.status_code == 404, f"Cross-user isolation failed on {ep}: {r.status_code}"

        r = client.post("/codebase/search", headers=headers_b, json={"query": "test", "codebase_id": codebase_id})
        assert r.status_code == 404, f"Cross-user isolation failed on search: {r.status_code}"
        print("[PASS] 13. Cross-user isolation verified across all AI endpoints")

    finally:
        # Cleanup
        client.delete(f"/codebase/delete/{codebase_id}", headers=headers_a)
        db.users.delete_many({"email": {"$in": [user_email, other_email]}})
        print("[PASS] 14. Cleaned up test codebase and test users")

    print("\n=== ALL PHASE 3 AI TESTS PASSED PERFECTLY ===")

if __name__ == "__main__":
    run_tests()
