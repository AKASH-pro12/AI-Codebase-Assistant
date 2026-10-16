def chunk_code(content: str, chunk_size: int = 40, overlap: int = 5):

    lines = content.splitlines()

    chunks = []

    start = 0
    chunk_index = 0

    while start < len(lines):

        end = start + chunk_size

        chunk = "\n".join(lines[start:end])

        chunks.append({
            "chunk_index": chunk_index,
            "content": chunk
        })

        chunk_index += 1

        start = end - overlap

    return chunks