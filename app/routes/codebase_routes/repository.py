from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import db
from app.utils.auth import get_current_user

router = APIRouter(tags=["Codebase Repository"])


def get_owned_codebase(codebase_id: str, user: dict) -> dict:
    """Return a codebase only if it belongs to the authenticated user."""
    codebase = db.codebases.find_one({
        "codebase_id": codebase_id,
        "user_id": str(user["_id"])
    })

    if not codebase:
        # Use 404 so codebase IDs belonging to other users aren't disclosed.
        raise HTTPException(
            status_code=404,
            detail="Codebase not found"
        )

    return codebase


@router.get("/stats")
def get_user_stats(
    current_user: dict = Depends(get_current_user)
):
    """Aggregates user-level metrics across all owned codebases."""
    user_id = str(current_user["_id"])
    codebases = list(db.codebases.find({"user_id": user_id}).sort("created_at", -1))

    total_codebases = len(codebases)
    total_files = sum(cb.get("total_files", len(cb.get("files", []))) for cb in codebases)
    total_chunks = db.code_chunks.count_documents({"user_id": user_id})

    # Detect technologies across all user codebases
    tech_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "React (JSX)",
        ".ts": "TypeScript",
        ".tsx": "React (TSX)",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".html": "HTML",
        ".css": "CSS",
        ".sql": "SQL",
        ".json": "JSON",
        ".md": "Markdown",
    }
    technologies_found = set()
    for cb in codebases:
        for f in cb.get("files", []):
            ext = f.get("extension", "").lower()
            if ext in tech_map:
                technologies_found.add(tech_map[ext])

    recent_activity = [
        {
            "codebase_id": cb.get("codebase_id"),
            "codebase_name": cb.get("codebase_name"),
            "total_files": cb.get("total_files", 0),
            "created_at": cb.get("created_at"),
        }
        for cb in codebases[:5]
    ]

    return {
        "total_codebases": total_codebases,
        "total_files": total_files,
        "total_chunks": total_chunks,
        "technologies": sorted(list(technologies_found)),
        "recent_activity": recent_activity,
    }


@router.get("/list")
def list_codebases(
    current_user: dict = Depends(get_current_user)
):
    codebases = db.codebases.find(
        {"user_id": str(current_user["_id"])},
        {
            "_id": 0,
            "codebase_id": 1,
            "codebase_name": 1,
            "total_files": 1,
            "created_at": 1
        }
    ).sort("created_at", -1)

    codebase_list = [
        {
            "codebase_id": codebase.get("codebase_id"),
            "codebase_name": codebase.get("codebase_name"),
            "total_files": codebase.get("total_files", 0),
            "created_at": codebase.get("created_at")
        }
        for codebase in codebases
    ]

    return {
        "total_codebases": len(codebase_list),
        "codebases": codebase_list
    }



@router.get("/details/{codebase_id}")
def get_codebase_details(
    codebase_id: str,
    current_user: dict = Depends(get_current_user)
):
    codebase = get_owned_codebase(codebase_id, current_user)
    files = codebase.get("files", [])

    return {
        "codebase_id": codebase.get("codebase_id"),
        "codebase_name": codebase.get("codebase_name"),
        "total_files": codebase.get("total_files", len(files)),
        "created_at": codebase.get("created_at"),
        "files": [
            {
                "relative_path": file_data.get("relative_path"),
                "extension": file_data.get("extension")
            }
            for file_data in files
        ]
    }


@router.delete("/delete/{codebase_id}")
def delete_codebase(
    codebase_id: str,
    current_user: dict = Depends(get_current_user)
):
    import os
    import shutil
    from app.services.file_processor import UPLOAD_DIR

    codebase = get_owned_codebase(codebase_id, current_user)

    # Only delete chunks associated with this owned codebase.
    chunks_result = db.code_chunks.delete_many({
        "codebase_id": codebase_id,
        "user_id": str(current_user["_id"])
    })

    codebase_result = db.codebases.delete_one({
        "_id": codebase["_id"],
        "user_id": str(current_user["_id"])
    })

    # Clean up extracted disk directory if present
    codebase_dir = os.path.join(UPLOAD_DIR, codebase_id)
    if os.path.exists(codebase_dir):
        shutil.rmtree(codebase_dir, ignore_errors=True)

    return {
        "message": "Codebase deleted successfully",
        "codebase_id": codebase_id,
        "deleted_codebase_documents": codebase_result.deleted_count,
        "deleted_chunks": chunks_result.deleted_count
    }


@router.get("/files")
def get_repository_files(
    codebase_id: str = Query(..., description="ID of the codebase"),
    current_user: dict = Depends(get_current_user)
):
    codebase = get_owned_codebase(codebase_id, current_user)
    files = [
        {
            "relative_path": file_data.get("relative_path"),
            "extension": file_data.get("extension")
        }
        for file_data in codebase.get("files", [])
    ]

    return {
        "codebase_id": codebase.get("codebase_id"),
        "codebase_name": codebase.get("codebase_name"),
        "total_files": codebase.get("total_files", len(files)),
        "files": files
    }


@router.get("/summary")
def get_repository_summary(
    codebase_id: str = Query(..., description="ID of the codebase"),
    current_user: dict = Depends(get_current_user)
):
    codebase = get_owned_codebase(codebase_id, current_user)
    files = codebase.get("files", [])

    extension_counter = Counter()
    directory_counter = Counter()

    for file_data in files:
        extension = file_data.get("extension")
        if extension:
            extension_counter[extension] += 1

        relative_path = file_data.get("relative_path", "")
        path_parts = relative_path.replace("\\", "/").split("/")

        if len(path_parts) > 1:
            directory_counter[path_parts[0]] += 1

    return {
        "codebase_id": codebase.get("codebase_id"),
        "codebase_name": codebase.get("codebase_name"),
        "total_files": codebase.get("total_files", len(files)),
        "file_types": [
            {"extension": extension, "count": count}
            for extension, count in extension_counter.most_common()
        ],
        "top_level_directories": [
            {"directory": directory, "file_count": count}
            for directory, count in directory_counter.most_common()
        ]
    }


@router.get("/technologies")
def get_repository_technologies(
    codebase_id: str = Query(..., description="ID of the codebase"),
    current_user: dict = Depends(get_current_user)
):
    codebase = get_owned_codebase(codebase_id, current_user)
    files = codebase.get("files", [])

    technology_rules = {
        "Python": {".py"},
        "JavaScript": {".js", ".jsx"},
        "TypeScript": {".ts", ".tsx"},
        "HTML": {".html"},
        "CSS": {".css"},
        "Java": {".java"},
        "C/C++": {".c", ".cpp", ".h"},
        "SQL": {".sql"},
        "Markdown": {".md"},
        "JSON": {".json"}
    }

    detected_technologies = []

    for technology, extensions in technology_rules.items():
        evidence = sorted({
            file_data.get("extension", "").lower()
            for file_data in files
            if file_data.get("extension", "").lower() in extensions
        })

        if evidence:
            detected_technologies.append({
                "name": technology,
                "evidence": evidence
            })

    return {
        "codebase_id": codebase.get("codebase_id"),
        "codebase_name": codebase.get("codebase_name"),
        "technologies": detected_technologies
    }


@router.get("/file")
def get_file_details(
    codebase_id: str = Query(..., description="ID of the codebase"),
    file_path: str = Query(
        ...,
        description="Relative path of the file inside the repository"
    ),
    current_user: dict = Depends(get_current_user)
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
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )

    stored_file_path = matching_file.get("file_path")

    chunks = list(db.code_chunks.find(
        {
            "codebase_id": codebase_id,
            "user_id": str(current_user["_id"]),
            "file_path": stored_file_path
        },
        {
            "_id": 0,
            "chunk_index": 1,
            "content": 1
        }
    ).sort("chunk_index", 1))

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No code content found for: {file_path}"
        )

    content = "\n".join(
        chunk.get("content", "")
        for chunk in chunks
    )

    return {
        "codebase_id": codebase_id,
        "file_path": requested_path,
        "extension": matching_file.get("extension"),
        "total_chunks": len(chunks),
        "content": content
    }
