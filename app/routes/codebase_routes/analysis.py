from fastapi import APIRouter, HTTPException, Query

from app.database import db
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



def get_matching_file(file_path: str):

    codebase = db.codebases.find_one(
        {},
        {"_id": 0, "files": 1},
        sort=[("created_at", -1)],
    )

    if not codebase:
        raise HTTPException(
            status_code=404,
            detail="No processed codebase found",
        )

    requested_path = file_path.replace("\\", "/")

    for file_data in codebase.get("files", []):
        stored_path = file_data.get(
            "relative_path",
            "",
        ).replace("\\", "/")

        if stored_path == requested_path:
            return file_data, codebase

    raise HTTPException(
        status_code=404,
        detail=f"File not found: {file_path}",
    )


def get_file_content(stored_file_path: str):

    chunks = list(
        db.code_chunks.find(
            {"file_path": stored_file_path},
            {
                "_id": 0,
                "chunk_index": 1,
                "content": 1,
            },
        ).sort("chunk_index", 1)
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No code content found",
        )

    content = "\n".join(
        chunk["content"]
        for chunk in chunks
    )

    return chunks, content



@router.get("/explain-file")
def explain_repository_file(
    file_path: str = Query(...),
):

    matching_file, _ = get_matching_file(
        file_path
    )

    chunks, content = get_file_content(
        matching_file["file_path"]
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



@router.get("/functions")
def get_file_functions(
    file_path: str = Query(...),
):

    matching_file, _ = get_matching_file(
        file_path
    )

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Function analysis supports only Python files",
        )

    functions = analyze_python_file(
        matching_file["file_path"]
    )

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_functions": len(functions),
        "functions": functions,
    }



@router.get("/classes")
def get_file_classes(
    file_path: str = Query(...),
):

    matching_file, _ = get_matching_file(
        file_path
    )

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Class analysis supports only Python files",
        )

    classes = analyze_python_classes(
        matching_file["file_path"]
    )

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_classes": len(classes),
        "classes": classes,
    }



@router.get("/routes")
def get_file_routes(
    file_path: str = Query(...),
):

    matching_file, _ = get_matching_file(
        file_path
    )

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Route analysis supports only Python files",
        )

    routes = analyze_python_routes(
        matching_file["file_path"]
    )

    return {
        "file_path": file_path,
        "extension": ".py",
        "total_routes": len(routes),
        "routes": routes,
    }



@router.get("/dependencies")
def get_file_dependencies(
    file_path: str = Query(...),
):

    matching_file, codebase = get_matching_file(
        file_path
    )

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Dependency analysis supports only Python files",
        )

    dependencies = analyze_python_dependencies(
        matching_file["file_path"]
    )

    repository_files = [
        file["file_path"]
        for file in codebase["files"]
        if file.get("file_path")
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
    file_path: str = Query(...),
):

    matching_file, codebase = get_matching_file(
        file_path
    )

    if matching_file["extension"].lower() != ".py":
        raise HTTPException(
            status_code=400,
            detail="Relationship analysis supports only Python files",
        )

    repository_files = [
        file["file_path"]
        for file in codebase["files"]
        if file.get("file_path")
    ]

    all_dependencies = []

    for repo_file in repository_files:

        if not repo_file.endswith(".py"):
            continue

        try:

            deps = analyze_python_dependencies(
                repo_file
            )

            local = resolve_local_dependencies(
                file_path=repo_file,
                dependencies=deps,
                repository_files=repository_files,
            )

            all_dependencies.extend(local)

        except Exception:
            continue

    relationships = build_repository_relationships(
        all_dependencies
    )

    current_file = matching_file["file_path"]

    outgoing = [
        rel
        for rel in relationships
        if rel["source_file"] == current_file
    ]

    incoming = [
        rel
        for rel in relationships
        if rel["target_file"] == current_file
    ]

    return {
        "file_path": file_path,
        "total_relationships": len(outgoing) + len(incoming),
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "outgoing_relationships": outgoing,
        "incoming_relationships": incoming,
    }