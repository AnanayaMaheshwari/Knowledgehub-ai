
import re


def split_into_chunks(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150
) -> list[str]:
    """
    Split text into smaller chunks with overlapping content.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size.")

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Avoid cutting words in the middle when possible.
        if end < len(text):
            boundary = text.rfind(" ", start, end)

            if boundary > start + chunk_size // 2:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def create_document_chunks(
    extracted_text: str,
    chunk_size: int = 1000,
    overlap: int = 150
) -> list[dict]:
    """
    Create chunks while preserving PDF page numbers.
    DOCX chunks will have page_number=None.
    """

    page_pattern = r"(?m)^\[Page (\d+)\]\s*$"

    matches = list(re.finditer(page_pattern, extracted_text))

    sections = []

    if matches:
        for index, match in enumerate(matches):
            start = match.end()
            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(extracted_text)
            )

            page_number = int(match.group(1))
            page_text = extracted_text[start:end].strip()

            sections.append((page_number, page_text))

    else:
        sections.append((None, extracted_text.strip()))

    document_chunks = []
    chunk_index = 0

    for page_number, page_text in sections:
        chunks = split_into_chunks(
            page_text,
            chunk_size,
            overlap
        )

        for chunk in chunks:
            document_chunks.append({
                "chunk_index": chunk_index,
                "content": chunk,
                "page_number": page_number
            })

            chunk_index += 1

    return document_chunks
