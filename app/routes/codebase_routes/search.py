from fastapi import APIRouter
from pydantic import BaseModel

from app.services.embedding import generate_embedding
from app.services.vector_search import search_similar_chunks
from app.services.llm import ask_llm


router = APIRouter(
    tags=["Codebase Search"]
)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    chat_history: list = []
    previous_sources: list = []


@router.post("/search")
def search_codebase(request: SearchRequest):

    query_embedding = generate_embedding(
        request.query
    )

    results = search_similar_chunks(
        query_embedding=query_embedding,
        limit=request.limit
    )

    context_parts = []

    for result in results:

        file_path = result.get(
            "file_path",
            ""
        )

        content = result.get(
            "content",
            ""
        )

        context_parts.append(
            f"""
FILE: {file_path}

CODE:
{content}
"""
        )

    context = "\n".join(
        context_parts
    )

    answer = ask_llm(
        question=request.query,
        context=context,
        chat_history=request.chat_history
    )

    return {
        "question": request.query,
        "answer": answer,
        "sources": [
            {
                "file_path": result.get(
                    "file_path"
                ),
                "score": result.get(
                    "score"
                )
            }
            for result in results
        ]
    }
