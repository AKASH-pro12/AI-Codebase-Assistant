from fastapi import APIRouter, HTTPException

from app.database import db
from app.services.issue_detector import analyze_python_issues
from app.services.code_improvement import (
    generate_code_improvements,
)


router = APIRouter(
    tags=["Code Improvements"]
)


@router.get("/improvements")
def get_code_improvements():

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "codebase_name": 1,
            "files": 1,
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

    repository_files = codebase.get(
        "files",
        []
    )

    all_issues = []
    scanned_files = 0

    for file_data in repository_files:

        file_path = file_data.get(
            "file_path"
        )

        extension = file_data.get(
            "extension",
            ""
        ).lower()

        if not file_path:
            continue

        if extension != ".py":
            continue

        scanned_files += 1

        try:

            issues = analyze_python_issues(
                file_path
            )

            all_issues.extend(
                issues
            )

        except (
            ValueError,
            OSError
        ):
            continue

    improvement_result = generate_code_improvements(
        issues=all_issues,
        chat_history=[]
    )

    return {
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "scanned_files": scanned_files,
        "total_issues": len(
            all_issues
        ),
        "improvements": improvement_result.get(
            "improvements"
        )
    }