from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.database import db

from app.services.file_processor import (
    save_and_extract_zip,
    get_code_files,
    read_code_files
)

from app.services.code_chunker import chunk_code
from app.services.embedding import generate_embedding
from app.services.vector_search import search_similar_chunks
from app.services.llm import ask_llm


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


@router.post("/search")
def search_codebase(request: SearchRequest):

# Build contextual search query

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

# Retrieve relevant code chunks

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

# Generate query embedding

        query_embedding = generate_embedding(
            search_query
        )

# Vector Search

        results = search_similar_chunks(
            query_embedding=query_embedding,
            limit=request.limit
        )

# Build code context

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


# Generate LLM Answer


    answer = ask_llm(
        question=request.query,
        context=context,
        chat_history=request.chat_history
    )

# Response

    return {
        "query": request.query,
        "answer": answer,
        "sources": results
    }