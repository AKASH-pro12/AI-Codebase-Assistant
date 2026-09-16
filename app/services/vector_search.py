from app.database import db


def search_similar_chunks(
    query_embedding: list,
    limit: int = 5
):

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
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

    results = db.code_chunks.aggregate(
        pipeline
    )

    return list(results)