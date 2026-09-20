
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import Query
from pydantic import BaseModel

from app.database import db

from app.routes.codebase_routes.upload import (
    router as upload_router
)

from app.routes.codebase_routes.repository import (
    router as repository_router
)

from app.routes.codebase_routes.analysis import (
    router as analysis_router
)

from app.routes.codebase_routes.architecture import (
    router as architecture_router
)

from app.services.vector_search import search_similar_chunks
from app.services.llm import ask_llm, explain_file
from app.services.function_analyzer import analyze_python_file
from app.services.class_analyzer import analyze_python_classes
from app.services.api_route_analyzer import analyze_python_routes

from app.services.dependency_analyzer import (
    analyze_python_dependencies,
    resolve_local_dependencies
)
from app.services.relationship_analyzer import (
    build_repository_relationships
)

from app.services.architecture_analyzer import (
    build_architecture_context
)

router = APIRouter(
    prefix="/codebase",
    tags=["Codebase"]
)

router.include_router(
    upload_router
)

router.include_router(
    repository_router
)

router.include_router(
    analysis_router
)

router.include_router(
    architecture_router
)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    chat_history: list = []
    previous_sources: list = []





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