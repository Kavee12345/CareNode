from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import settings


def chunk_text(text: str, doc_type: str) -> list[str]:
    """
    Split text into chunks appropriate for the document type.
    Lab reports use smaller chunks to preserve test-value-reference triples.
    """
    if not text or not text.strip():
        return []

    if doc_type == "lab_report":
        return _chunk_lab_report(text)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]


def _chunk_lab_report(text: str) -> list[str]:
    """
    For lab reports, split by line groups (each test = its own chunk)
    so the vector search preserves test-value-reference-range context.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    chunks = []
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line)
        # Start new chunk if current is getting big enough and line looks like a new section
        if current_len + line_len > 400 and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_len = 0

        current_chunk.append(line)
        current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # If chunks are too small, merge back up to min size
    return _merge_small_chunks(chunks, min_size=80)


def _merge_small_chunks(chunks: list[str], min_size: int = 80) -> list[str]:
    merged = []
    buffer = ""
    for chunk in chunks:
        if len(buffer) + len(chunk) < min_size:
            buffer = (buffer + "\n" + chunk).strip()
        else:
            if buffer:
                merged.append(buffer)
            buffer = chunk
    if buffer:
        merged.append(buffer)
    return merged
