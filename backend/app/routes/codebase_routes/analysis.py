from fastapi import APIRouter, HTTPException, Query, Depends

from app.database import db
from app.utils.auth import get_current_user
from app.services.llm import explain_file
from app.services.function_analyzer import analyze_python_file
from app.services.class_analyzer import analyze_python_classes
from app.services.api_route_analyzer import analyze_python_routes
from app.services.dependency_analyzer import (
    analyze_python_dependencies,
    resolve_local_dependencies,
)
from app.services.relationship_analyzer import (
    build_repository_relationships,
)

router = APIRouter(tags=["Code Analysis"])


def get_owned_codebase(codebase_id: str, user: dict) -> dict:
    """Return a codebase document only if it belongs to the authenticated user."""
    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id,
            "user_id": str(user["_id"]),
        }
    )
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")
    return codebase


def get_matching_file(file_path: str, codebase: dict):
    requested_path = file_path.replace("\\", "/")

    for file_data in codebase.get("files", []):
        stored_path = file_data.get("relative_path", "").replace("\\", "/")
        if stored_path == requested_path:
            return file_data

    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


def get_file_content(stored_file_path: str, codebase_id: str, user_id: str):
    chunks = list(
        db.code_chunks.find(
            {
                "file_path": stored_file_path,
                "codebase_id": codebase_id,
                "user_id": user_id,
            },
            {"_id": 0, "chunk_index": 1, "content": 1},
        ).sort("chunk_index", 1)
    )

    if not chunks:
        raise HTTPException(status_code=404, detail="No code content found")

    content = "\n".join(chunk["content"] for chunk in chunks)
    return chunks, content


@router.get("/explain-file")
def explain_repository_file(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(..., description="Relative file path within the codebase"),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)
    matching_file = get_matching_file(file_path, codebase)
    chunks, content = get_file_content(
        matching_file["file_path"], codebase_id, str(current_user["_id"])
    )

    explanation = explain_file(
        file_path=file_path,
        extension=matching_file["extension"],
        content=content,
    )

    return {
        "file_path": file_path,
        "extension": matching_file["extension"],
        "total_chunks": len(chunks),
        "explanation": explanation,
    }


import os


def resolve_file_source(stored_file_path: str, codebase_id: str, user_id: str) -> str | None:
    if os.path.exists(stored_file_path):
        return None
    try:
        _, content = get_file_content(stored_file_path, codebase_id, user_id)
        return content
    except Exception:
        return None


@router.get("/functions")
def get_file_functions(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)
    matching_file = get_matching_file(file_path, codebase)

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Function analysis supports only Python files",
        )

    stored_path = matching_file["file_path"]
    source_code = resolve_file_source(stored_path, codebase_id, str(current_user["_id"]))
    functions = analyze_python_file(stored_path, source_code=source_code)

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_functions": len(functions),
        "functions": functions,
    }


@router.get("/classes")
def get_file_classes(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)
    matching_file = get_matching_file(file_path, codebase)

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Class analysis supports only Python files",
        )

    stored_path = matching_file["file_path"]
    source_code = resolve_file_source(stored_path, codebase_id, str(current_user["_id"]))
    classes = analyze_python_classes(stored_path, source_code=source_code)

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_classes": len(classes),
        "classes": classes,
    }


@router.get("/routes")
def get_file_routes(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)
    matching_file = get_matching_file(file_path, codebase)

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Route analysis supports only Python files",
        )

    stored_path = matching_file["file_path"]
    source_code = resolve_file_source(stored_path, codebase_id, str(current_user["_id"]))
    routes = analyze_python_routes(stored_path, source_code=source_code)

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_routes": len(routes),
        "routes": routes,
    }


@router.get("/dependencies")
def get_file_dependencies(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)
    matching_file = get_matching_file(file_path, codebase)

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Dependency analysis supports only Python files",
        )

    stored_path = matching_file["file_path"]
    source_code = resolve_file_source(stored_path, codebase_id, str(current_user["_id"]))
    dependencies = analyze_python_dependencies(stored_path, source_code=source_code)

    repository_files = [
        f["file_path"] for f in codebase["files"] if f.get("file_path")
    ]

    local_dependencies = resolve_local_dependencies(
        file_path=matching_file["file_path"],
        dependencies=dependencies,
        repository_files=repository_files,
    )

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_imports": len(dependencies),
        "total_local_dependencies": len(local_dependencies),
        "imports": dependencies,
        "local_dependencies": local_dependencies,
    }


@router.get("/relationships")
def get_file_relationships(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    codebase = get_owned_codebase(codebase_id, current_user)
    matching_file = get_matching_file(file_path, codebase)

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Relationship analysis supports only Python files",
        )

    repository_files = [
        f["file_path"] for f in codebase["files"] if f.get("file_path")
    ]

    all_dependencies = []

    for repo_file in repository_files:
        if not repo_file.endswith(".py"):
            continue
        try:
            s_code = resolve_file_source(repo_file, codebase_id, str(current_user["_id"]))
            deps = analyze_python_dependencies(repo_file, source_code=s_code)
            local = resolve_local_dependencies(
                file_path=repo_file,
                dependencies=deps,
                repository_files=repository_files,
            )
            all_dependencies.extend(local)
        except Exception:
            continue

    relationships = build_repository_relationships(all_dependencies)

    current_file = matching_file["file_path"]
    outgoing = [r for r in relationships if r["source_file"] == current_file]
    incoming = [r for r in relationships if r["target_file"] == current_file]

    return {
        "file_path": file_path,
        "total_relationships": len(outgoing) + len(incoming),
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "outgoing_relationships": outgoing,
        "incoming_relationships": incoming,
    }