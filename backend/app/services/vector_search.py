import numpy as np
from app.database import db


def search_similar_chunks(
    query_embedding: list,
    codebase_id: str,
    limit: int = 5
):
    # 1. Try MongoDB Atlas Vector Search first
    try:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": limit,
                    "filter": {
                        "codebase_id": codebase_id
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "codebase_id": 1,
                    "file_path": 1,
                    "extension": 1,
                    "chunk_index": 1,
                    "content": 1,
                    "score": {
                        "$meta": "vectorSearchScore"
                    }
                }
            }
        ]

        results = list(db.code_chunks.aggregate(pipeline))
        if results:
            return results
    except Exception:
        # Atlas search failed or is indexing; fall back to in-memory cosine similarity
        pass

    # 2. Resilient fallback: exact cosine similarity across chunks of this codebase
    chunks = list(db.code_chunks.find(
        {"codebase_id": codebase_id},
        {"_id": 0, "codebase_id": 1, "file_path": 1, "extension": 1, "chunk_index": 1, "content": 1, "embedding": 1}
    ))
    if not chunks:
        return []

    q_vec = np.array(query_embedding, dtype=np.float32)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []

    scored_chunks = []
    for chunk in chunks:
        emb = chunk.get("embedding")
        if not emb or len(emb) != len(query_embedding):
            continue
        c_vec = np.array(emb, dtype=np.float32)
        c_norm = np.linalg.norm(c_vec)
        score = float(np.dot(q_vec, c_vec) / (q_norm * c_norm)) if c_norm != 0 else 0.0

        chunk_copy = {k: v for k, v in chunk.items() if k != "embedding"}
        chunk_copy["score"] = score
        scored_chunks.append(chunk_copy)

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:limit]