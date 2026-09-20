from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.database import db

from app.services.file_processor import (
    save_and_extract_zip,
    get_code_files,
    read_code_files,
    get_repository_metadata
)

from app.services.code_chunker import chunk_code
from app.services.embedding import generate_embedding


router = APIRouter(
    tags=["Codebase Upload"]
)


@router.post("/upload")
def upload_codebase(
    file: UploadFile = File(...)
):

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