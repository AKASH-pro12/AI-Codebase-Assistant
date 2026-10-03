from collections import Counter

from fastapi import APIRouter, HTTPException, Query

from app.database import db


router = APIRouter(
    tags=["Codebase Repository"]
)


@router.get("/list")
def list_codebases():

    codebases = db.codebases.find(
        {},
        {
            "_id": 0,
            "codebase_id": 1,
            "codebase_name": 1,
            "total_files": 1,
            "created_at": 1
        }
    ).sort(
        "created_at",
        -1
    )

    codebase_list = []

    for codebase in codebases:

        codebase_list.append({
            "codebase_id": codebase.get(
                "codebase_id"
            ),
            "codebase_name": codebase.get(
                "codebase_name"
            ),
            "total_files": codebase.get(
                "total_files",
                0
            ),
            "created_at": codebase.get(
                "created_at"
            )
        })

    return {
        "total_codebases": len(
            codebase_list
        ),
        "codebases": codebase_list
    }


@router.get("/details/{codebase_id}")
def get_codebase_details(
    codebase_id: str
):

    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id
        },
        {
            "_id": 0,
            "codebase_id": 1,
            "codebase_name": 1,
            "total_files": 1,
            "files": 1,
            "created_at": 1
        }
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail=f"Codebase not found: {codebase_id}"
        )

    files = codebase.get(
        "files",
        []
    )

    return {
        "codebase_id": codebase.get(
            "codebase_id"
        ),
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "total_files": codebase.get(
            "total_files",
            len(files)
        ),
        "created_at": codebase.get(
            "created_at"
        ),
        "files": [
            {
                "relative_path": file_data.get(
                    "relative_path"
                ),
                "extension": file_data.get(
                    "extension"
                )
            }
            for file_data in files
        ]
    }


@router.delete("/delete/{codebase_id}")
def delete_codebase(
    codebase_id: str
):

    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id
        }
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail=f"Codebase not found: {codebase_id}"
        )

    chunks_result = db.code_chunks.delete_many(
        {
            "codebase_id": codebase_id
        }
    )

    codebase_result = db.codebases.delete_one(
        {
            "codebase_id": codebase_id
        }
    )

    return {
        "message": "Codebase deleted successfully",
        "codebase_id": codebase_id,
        "deleted_codebase_documents": (
            codebase_result.deleted_count
        ),
        "deleted_chunks": (
            chunks_result.deleted_count
        )
    }


@router.get("/files")
def get_repository_files(
    codebase_id: str = Query(
        ...,
        description="ID of the codebase"
    )
):

    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id
        },
        {
            "_id": 0,
            "codebase_id": 1,
            "codebase_name": 1,
            "total_files": 1,
            "files": 1
        }
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail=f"Codebase not found: {codebase_id}"
        )

    files = []

    for file_data in codebase.get(
        "files",
        []
    ):

        files.append({
            "relative_path": file_data.get(
                "relative_path"
            ),
            "extension": file_data.get(
                "extension"
            )
        })

    return {
        "codebase_id": codebase.get(
            "codebase_id"
        ),
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "total_files": codebase.get(
            "total_files",
            len(files)
        ),
        "files": files
    }


@router.get("/summary")
def get_repository_summary(
    codebase_id: str = Query(
        ...,
        description="ID of the codebase"
    )
):

    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id
        },
        {
            "_id": 0,
            "codebase_id": 1,
            "codebase_name": 1,
            "total_files": 1,
            "files": 1
        }
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail=f"Codebase not found: {codebase_id}"
        )

    files = codebase.get(
        "files",
        []
    )

    extension_counter = Counter()
    directory_counter = Counter()

    for file_data in files:

        extension = file_data.get(
            "extension"
        )

        if extension:

            extension_counter[
                extension
            ] += 1

        relative_path = file_data.get(
            "relative_path",
            ""
        )

        path_parts = relative_path.replace(
            "\\",
            "/"
        ).split("/")

        if len(path_parts) > 1:

            top_level_directory = path_parts[0]

            directory_counter[
                top_level_directory
            ] += 1

    file_types = [
        {
            "extension": extension,
            "count": count
        }
        for extension, count
        in extension_counter.most_common()
    ]

    directories = [
        {
            "directory": directory,
            "file_count": count
        }
        for directory, count
        in directory_counter.most_common()
    ]

    return {
        "codebase_id": codebase.get(
            "codebase_id"
        ),
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "total_files": codebase.get(
            "total_files",
            len(files)
        ),
        "file_types": file_types,
        "top_level_directories": directories
    }


@router.get("/technologies")
def get_repository_technologies(
    codebase_id: str = Query(
        ...,
        description="ID of the codebase"
    )
):

    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id
        },
        {
            "_id": 0,
            "codebase_id": 1,
            "codebase_name": 1,
            "files": 1
        }
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail=f"Codebase not found: {codebase_id}"
        )

    files = codebase.get(
        "files",
        []
    )

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

        evidence = []

        for file_data in files:

            extension = file_data.get(
                "extension",
                ""
            ).lower()

            if extension in extensions:

                evidence.append(
                    extension
                )

        evidence = sorted(
            set(evidence)
        )

        if evidence:

            detected_technologies.append({
                "name": technology,
                "evidence": evidence
            })

    return {
        "codebase_id": codebase.get(
            "codebase_id"
        ),
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "technologies": detected_technologies
    }


@router.get("/file")
def get_file_details(
    codebase_id: str = Query(
        ...,
        description="ID of the codebase"
    ),
    file_path: str = Query(
        ...,
        description="Relative path of the file inside the repository"
    )
):

    codebase = db.codebases.find_one(
        {
            "codebase_id": codebase_id
        },
        {
            "_id": 0,
            "codebase_id": 1,
            "files": 1
        }
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail=f"Codebase not found: {codebase_id}"
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

    stored_file_path = matching_file.get(
        "file_path"
    )

    chunks = list(
        db.code_chunks.find(
            {
                "codebase_id": codebase_id,
                "file_path": stored_file_path
            },
            {
                "_id": 0,
                "chunk_index": 1,
                "content": 1
            }
        ).sort(
            "chunk_index",
            1
        )
    )

    if not chunks:

        raise HTTPException(
            status_code=404,
            detail=f"No code content found for: {file_path}"
        )

    content_parts = []

    for chunk in chunks:

        content_parts.append(
            chunk.get(
                "content",
                ""
            )
        )

    content = "\n".join(
        content_parts
    )

    return {
        "codebase_id": codebase_id,
        "file_path": requested_path,
        "extension": matching_file.get(
            "extension"
        ),
        "total_chunks": len(chunks),
        "content": content
    }