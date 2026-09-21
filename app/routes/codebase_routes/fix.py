from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.services.issue_detector import analyze_python_issues
from app.services.source_context import get_source_context
from app.services.code_fix import generate_code_fix


router = APIRouter(
    tags=["Code Fix"]
)


@router.get("/fix")
def get_code_fix(
    file_path: str = Query(
        ...,
        description="Relative path of the Python file"
    ),
    line_number: int = Query(
        ...,
        ge=1,
        description="Line number of the detected issue"
    )
):

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "files": 1
        },
        sort=[
            ("created_at", -1)
        ]
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail="No processed codebase found"
        )

    requested_path = file_path.replace(
        "\\",
        "/"
    )

    matching_file = None

    for file_data in codebase.get(
        "files",
        []
    ):

        stored_path = file_data.get(
            "relative_path",
            ""
        ).replace(
            "\\",
            "/"
        )

        if stored_path == requested_path:

            matching_file = file_data
            break

    if not matching_file:

        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )

    if matching_file.get(
        "extension",
        ""
    ).lower() != ".py":

        raise HTTPException(
            status_code=400,
            detail="Code fix currently supports only Python files"
        )

    stored_file_path = matching_file.get(
        "file_path"
    )

    if not stored_file_path:

        raise HTTPException(
            status_code=404,
            detail="Stored file path not found"
        )

    try:

        issues = analyze_python_issues(
            stored_file_path
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    matching_issue = None

    for issue in issues:

        if issue.get(
            "line_number"
        ) == line_number:

            matching_issue = issue
            break

    if not matching_issue:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No detected issue found at "
                f"{file_path}:{line_number}"
            )
        )

    matching_issue["file_path"] = (
        requested_path
    )

    source_context = get_source_context(
        file_path=stored_file_path,
        line_number=line_number,
        context_lines=5
    )

    if not source_context:

        raise HTTPException(
            status_code=404,
            detail="Source context not available"
        )

    result = generate_code_fix(
        issue=matching_issue,
        source_context=source_context,
        chat_history=[]
    )

    return {
        "file_path": requested_path,
        "line_number": line_number,
        "issue": {
            "severity": matching_issue.get(
                "severity"
            ),
            "issue_type": matching_issue.get(
                "issue_type"
            ),
            "message": matching_issue.get(
                "message"
            )
        },
        "source_context": source_context,
        "suggested_fix": result.get(
            "suggested_fix"
        )
    }