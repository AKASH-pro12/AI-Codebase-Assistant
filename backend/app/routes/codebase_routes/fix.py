from fastapi import APIRouter, HTTPException, Query, Depends

from app.database import db
from app.utils.auth import get_current_user
from app.services.issue_detector import analyze_python_issues
from app.services.source_context import get_source_context
from app.services.code_fix import generate_code_fix


router = APIRouter(tags=["Code Fix"])


def get_owned_codebase(codebase_id: str, user: dict) -> dict:
    codebase = db.codebases.find_one(
        {"codebase_id": codebase_id, "user_id": str(user["_id"])}
    )
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")
    return codebase


@router.get("/fix")
def get_code_fix(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(..., description="Relative path of the Python file"),
    line_number: int = Query(..., ge=1, description="Line number of the detected issue"),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)

    requested_path = file_path.replace("\\", "/")
    matching_file = None

    for file_data in codebase.get("files", []):
        stored_path = file_data.get("relative_path", "").replace("\\", "/")
        if stored_path == requested_path:
            matching_file = file_data
            break

    if not matching_file:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if matching_file.get("extension", "").lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Code fix currently supports only Python files",
        )

    stored_file_path = matching_file.get("file_path")
    if not stored_file_path:
        raise HTTPException(status_code=404, detail="Stored file path not found")

    import os

    source_code = None
    if not os.path.exists(stored_file_path):
        chunks = list(db.code_chunks.find(
            {"file_path": stored_file_path, "codebase_id": codebase_id, "user_id": str(current_user["_id"])},
            {"_id": 0, "chunk_index": 1, "content": 1}
        ).sort("chunk_index", 1))
        if chunks:
            source_code = "\n".join(c["content"] for c in chunks)

    try:
        issues = analyze_python_issues(stored_file_path, source_code=source_code)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    matching_issue = None
    for issue in issues:
        if issue.get("line_number") == line_number:
            matching_issue = issue
            break

    if not matching_issue:
        raise HTTPException(
            status_code=404,
            detail=f"No detected issue found at {file_path}:{line_number}",
        )

    matching_issue["file_path"] = requested_path

    source_context = get_source_context(
        file_path=stored_file_path,
        line_number=line_number,
        context_lines=5,
        source_code=source_code,
    )

    if not source_context:
        raise HTTPException(status_code=404, detail="Source context not available")

    result = generate_code_fix(
        issue=matching_issue,
        source_context=source_context,
        chat_history=[],
    )

    return {
        "codebase_id": codebase_id,
        "file_path": requested_path,
        "line_number": line_number,
        "issue": {
            "severity": matching_issue.get("severity"),
            "issue_type": matching_issue.get("issue_type"),
            "message": matching_issue.get("message"),
        },
        "source_context": source_context,
        "suggested_fix": result.get("suggested_fix"),
    }