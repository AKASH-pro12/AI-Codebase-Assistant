from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import db
from app.utils.auth import get_current_user
from app.services.issue_detector import analyze_python_issues


router = APIRouter(tags=["Codebase Issues"])


def get_owned_codebase(codebase_id: str, user: dict) -> dict:
    codebase = db.codebases.find_one(
        {"codebase_id": codebase_id, "user_id": str(user["_id"])}
    )
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")
    return codebase


@router.get("/issues")
def get_repository_issues(
    codebase_id: str = Query(..., description="ID of the codebase"),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)

    repository_files = codebase.get("files", [])
    all_issues = []
    scanned_files = 0

    # Build a mapping from stored absolute file_path -> relative_path for display
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
            # Replace absolute path with relative path for the response
            relative = path_to_relative.get(file_path, file_path)
            for issue in issues:
                issue["file_path"] = relative
            all_issues.extend(issues)
        except (ValueError, OSError):
            continue

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for issue in all_issues:
        severity = issue.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1

    return {
        "codebase_id": codebase_id,
        "codebase_name": codebase.get("codebase_name"),
        "scanned_files": scanned_files,
        "total_issues": len(all_issues),
        "severity_counts": severity_counts,
        "issues": all_issues,
    }