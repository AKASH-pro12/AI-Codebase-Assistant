from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import Query
from pydantic import BaseModel

from app.database import db

from app.services.file_processor import (
    save_and_extract_zip,
    get_code_files,
    read_code_files,
    get_repository_metadata
)

from app.services.code_chunker import chunk_code
from app.services.embedding import generate_embedding
from app.services.vector_search import search_similar_chunks
from app.services.llm import ask_llm, explain_file


router = APIRouter(
    prefix="/codebase",
    tags=["Codebase"]
)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    chat_history: list = []
    previous_sources: list = []


@router.post("/upload")
def upload_codebase(file: UploadFile = File(...)):

    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are allowed"
        )

    file_data = file.file.read()

    extract_dir = save_and_extract_zip(
        file_data,
        file.filename
    )

    code_files = get_code_files(
        extract_dir
    )

    files_data = read_code_files(
        code_files
    )

    repository_metadata = get_repository_metadata(
        extract_dir,
        code_files
    )

    codebase_document = {
        "codebase_name": file.filename,
        "total_files": repository_metadata["total_files"],
        "files": repository_metadata["files"],
        "created_at": datetime.now(timezone.utc)
    }

    db.codebases.insert_one(
        codebase_document
    )

    all_chunks = []

    for file_data in files_data:

        chunks = chunk_code(
            file_data["content"]
        )

        for chunk in chunks:

            embedding_text = f"""
File: {file_data["file_path"]}
Extension: {file_data["extension"]}

Code:
{chunk["content"]}
"""

            embedding = generate_embedding(
                embedding_text
            )

            all_chunks.append({
                "file_path": file_data["file_path"],
                "extension": file_data["extension"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": embedding
            })

    if all_chunks:

        db.code_chunks.insert_many(
            all_chunks
        )

    return {
        "message": "Codebase processed and stored successfully",
        "filename": file.filename,
        "total_files": len(files_data),
        "total_chunks": len(all_chunks)
    }


@router.get("/files")
def get_repository_files():

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "codebase_name": 1,
            "total_files": 1,
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
def get_repository_summary():

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "codebase_name": 1,
            "total_files": 1,
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
def get_repository_technologies():

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "codebase_name": 1,
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
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "technologies": detected_technologies
    }


@router.get("/file")
def get_file_details(
    file_path: str = Query(
        ...,
        description="Relative path of the file inside the repository"
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

    stored_file_path = matching_file.get(
        "file_path"
    )

    chunks = list(
        db.code_chunks.find(
            {
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
        "file_path": requested_path,
        "extension": matching_file.get(
            "extension"
        ),
        "total_chunks": len(chunks),
        "content": content
    }


@router.get("/explain-file")
def explain_repository_file(
    file_path: str = Query(
        ...,
        description="Relative path of the file inside the repository"
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

    stored_file_path = matching_file.get(
        "file_path"
    )

    chunks = list(
        db.code_chunks.find(
            {
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

    explanation = explain_file(
        file_path=requested_path,
        extension=matching_file.get(
            "extension",
            ""
        ),
        content=content
    )

    return {
        "file_path": requested_path,
        "extension": matching_file.get(
            "extension"
        ),
        "total_chunks": len(chunks),
        "explanation": explanation
    }


@router.post("/search")
def search_codebase(request: SearchRequest):

    search_query = request.query

    if request.chat_history:

        previous_messages = []

        for message in request.chat_history[-6:]:

            role = message.get("role", "")
            content = message.get("content", "")

            if content:

                previous_messages.append(
                    f"{role}: {content}"
                )

        if previous_messages:

            search_query = (
                "\n".join(previous_messages)
                + "\n"
                + request.query
            )

    if request.previous_sources:

        previous_files = list(
            dict.fromkeys(
                request.previous_sources
            )
        )

        python_files = [
            file_path
            for file_path in previous_files
            if file_path.lower().endswith(".py")
        ]

        if python_files:
            previous_file = python_files[0]
        else:
            previous_file = previous_files[0]

        results = list(
            db.code_chunks.find(
                {
                    "file_path": previous_file
                },
                {
                    "_id": 0,
                    "file_path": 1,
                    "extension": 1,
                    "chunk_index": 1,
                    "content": 1
                }
            ).sort(
                "chunk_index",
                1
            )
        )

        results = results[:request.limit]

    else:

        query_embedding = generate_embedding(
            search_query
        )

        results = search_similar_chunks(
            query_embedding=query_embedding,
            limit=request.limit
        )

    context_parts = []

    for result in results:

        context_parts.append(
            f"""
File: {result["file_path"]}
Chunk: {result["chunk_index"]}

Code:
{result["content"]}
"""
        )

    context = "\n\n".join(
        context_parts
    )

    answer = ask_llm(
        question=request.query,
        context=context,
        chat_history=request.chat_history
    )

    return {
        "query": request.query,
        "answer": answer,
        "sources": results
    }