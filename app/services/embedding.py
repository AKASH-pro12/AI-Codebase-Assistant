from typing import Optional

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embedding(text: str):
    model = get_model()
    embedding = model.encode(text)
    return embedding.tolist()