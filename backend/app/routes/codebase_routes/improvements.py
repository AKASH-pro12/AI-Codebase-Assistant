from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import db
from app.utils.auth import get_current_user
from app.services.issue_detector import analyze_python_issues
from app.services.code_improvement import generate_code_improvements


router = APIRouter(tags=["Code Improvements"])


def get_owned_codebase(codebase_id: str, user: dict) -> dict:
    codebase = db.codebases.find_one(
        {"codebase_id": codebase_id, "user_id": str(user["_id"])}
    )
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")
    return codebase


@router.get("/improvements")
def get_code_improvements(
    codebase_id: str = Query(..., description="ID of the codebase"),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)

    repository_files = codebase.get("files", [])
    all_issues = []
    scanned_files = 0

    path_to_relative = {
        fd["file_path"]: fd["relative_path"]
        for fd in repository_files
        if fd.get("file_path") and fd.get("relative_path")
    }

    import os

    for file_data in repository_files:
        file_path = file_data.get("file_path")
        extension = file_data.get("extension", "").lower()

        if not file_path or extension != ".py":
            continue

        scanned_files += 1

        try:
            source_code = None
            if not os.path.exists(file_path):
                chunks = list(db.code_chunks.find(
                    {"file_path": file_path, "codebase_id": codebase_id, "user_id": str(current_user["_id"])},
                    {"_id": 0, "chunk_index": 1, "content": 1}
                ).sort("chunk_index", 1))
                if chunks:
                    source_code = "\n".join(c["content"] for c in chunks)

            issues = analyze_python_issues(file_path, source_code=source_code)
            relative = path_to_relative.get(file_path, file_path)
            for issue in issues:
                issue["file_path"] = relative
            all_issues.extend(issues)
        except (ValueError, OSError):
            continue

    improvement_result = generate_code_improvements(
        issues=all_issues,
        chat_history=[],
    )

    return {
        "codebase_id": codebase_id,
        "codebase_name": codebase.get("codebase_name"),
        "scanned_files": scanned_files,
        "total_issues": len(all_issues),
        "improvements": improvement_result.get("improvements"),
    }