from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.utils.auth import get_current_user
from app.database import db
from app.services.embedding import generate_embedding
from app.services.vector_search import search_similar_chunks
from app.services.llm import ask_llm


router = APIRouter(tags=["Codebase Search"])


class SearchRequest(BaseModel):
    query: str
    codebase_id: str
    limit: int = 5
    chat_history: list = []
    previous_sources: list = []


@router.post("/search")
def search_codebase(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    # Verify ownership before searching
    codebase = db.codebases.find_one(
        {
            "codebase_id": request.codebase_id,
            "user_id": str(current_user["_id"]),
        }
    )
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")

    query_embedding = generate_embedding(request.query)

    results = search_similar_chunks(
        query_embedding=query_embedding,
        codebase_id=request.codebase_id,
        limit=request.limit,
    )

    context_parts = []
    for result in results:
        file_path = result.get("file_path", "")
        content = result.get("content", "")
        context_parts.append(
            f"\nFILE: {file_path}\n\nCODE:\n{content}\n"
        )

    context = "\n".join(context_parts)

    answer = ask_llm(
        question=request.query,
        context=context,
        chat_history=request.chat_history,
    )

    return {
        "question": request.query,
        "codebase_id": request.codebase_id,
        "answer": answer,
        "sources": [
            {
                "file_path": result.get("file_path"),
                "score": result.get("score"),
            }
            for result in results
        ],
    }