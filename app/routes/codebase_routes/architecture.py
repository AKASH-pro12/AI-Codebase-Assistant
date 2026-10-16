from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import db
from app.utils.auth import get_current_user
from app.services.architecture_analyzer import build_architecture_context
from app.services.llm import ask_llm


router = APIRouter(tags=["Architecture"])


def get_owned_codebase(codebase_id: str, user: dict) -> dict:
    codebase = db.codebases.find_one(
        {"codebase_id": codebase_id, "user_id": str(user["_id"])}
    )
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")
    return codebase


@router.get("/architecture")
def get_repository_architecture(
    codebase_id: str = Query(..., description="ID of the codebase"),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)

    repository_files = codebase.get("files", [])
    technologies = codebase.get("technologies", [])

    import os

    def resolve_source(fp):
        if os.path.exists(fp):
            return None
        chunks = list(db.code_chunks.find(
            {"file_path": fp, "codebase_id": codebase_id, "user_id": str(current_user["_id"])},
            {"_id": 0, "chunk_index": 1, "content": 1}
        ).sort("chunk_index", 1))
        return "\n".join(c["content"] for c in chunks) if chunks else None

    routes = []
    for file_data in repository_files:
        file_path = file_data.get("file_path")
        extension = file_data.get("extension", "").lower()

        if not file_path or extension != ".py":
            continue

        try:
            from app.services.api_route_analyzer import analyze_python_routes

            s_code = resolve_source(file_path)
            file_routes = analyze_python_routes(file_path, source_code=s_code)
            for route in file_routes:
                routes.append({**route, "file_path": file_path})
        except Exception:
            continue

    relationships = []
    try:
        from app.services.dependency_analyzer import (
            analyze_python_dependencies,
            resolve_local_dependencies,
        )
        from app.services.relationship_analyzer import build_repository_relationships

        repository_file_paths = [
            fd.get("file_path")
            for fd in repository_files
            if fd.get("file_path")
        ]

        all_local_dependencies = []
        for fp in repository_file_paths:
            if not fp.endswith(".py"):
                continue
            try:
                s_code = resolve_source(fp)
                dependencies = analyze_python_dependencies(fp, source_code=s_code)
                local_dependencies = resolve_local_dependencies(
                    file_path=fp,
                    dependencies=dependencies,
                    repository_files=repository_file_paths,
                )
                all_local_dependencies.extend(local_dependencies)
            except Exception:
                continue

        relationships = build_repository_relationships(all_local_dependencies)
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
            "Describe the major components, how files are related, "
            "how API routes connect to the application, "
            "and the overall application flow."
        ),
        context=architecture_context,
        chat_history=[],
    )

    return {
        "codebase_id": codebase_id,
        "codebase_name": codebase.get("codebase_name"),
        "total_files": len(repository_files),
        "total_routes": len(routes),
        "total_relationships": len(relationships),
        "architecture_context": architecture_context,
        "architecture_explanation": architecture_explanation,
    }