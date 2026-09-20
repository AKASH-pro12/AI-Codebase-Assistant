from fastapi import APIRouter, HTTPException

from app.database import db
from app.services.architecture_analyzer import (
    build_architecture_context,
)
from app.services.llm import ask_llm


router = APIRouter(
    tags=["Architecture"]
)


@router.get("/architecture")
def get_repository_architecture():

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "codebase_name": 1,
            "files": 1,
            "technologies": 1,
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

    technologies = codebase.get(
        "technologies",
        []
    )

    routes = []

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

        try:

            from app.services.api_route_analyzer import (
                analyze_python_routes
            )

            file_routes = analyze_python_routes(
                file_path
            )

            for route in file_routes:

                routes.append({
                    **route,
                    "file_path": file_path
                })

        except Exception:
            continue

    relationships = []

    try:

        from app.services.dependency_analyzer import (
            analyze_python_dependencies,
            resolve_local_dependencies,
        )

        from app.services.relationship_analyzer import (
            build_repository_relationships,
        )

        repository_file_paths = [
            file_data.get("file_path")
            for file_data in repository_files
            if file_data.get("file_path")
        ]

        all_local_dependencies = []

        for file_path in repository_file_paths:

            if not file_path.endswith(".py"):
                continue

            try:

                dependencies = analyze_python_dependencies(
                    file_path
                )

                local_dependencies = (
                    resolve_local_dependencies(
                        file_path=file_path,
                        dependencies=dependencies,
                        repository_files=repository_file_paths,
                    )
                )

                all_local_dependencies.extend(
                    local_dependencies
                )

            except Exception:
                continue

        relationships = build_repository_relationships(
            all_local_dependencies
        )

    except Exception:
        relationships = []

    architecture_context = build_architecture_context(
        repository_files=repository_files,
        technologies=technologies,
        routes=routes,
        relationships=relationships,
    )

    architecture_explanation = ask_llm(
        question=(
            "Explain the architecture of this repository. "
            "Describe the major components, how files are "
            "related, how API routes connect to the application, "
            "and the overall application flow."
        ),
        context=architecture_context,
        chat_history=[],
    )

    return {
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "total_files": len(
            repository_files
        ),
        "total_routes": len(
            routes
        ),
        "total_relationships": len(
            relationships
        ),
        "architecture_context": architecture_context,
        "architecture_explanation": architecture_explanation,
    }