
from app.services.embedding_service import generate_embedding


def search_documents(
    supabase,
    query: str,
    match_count: int = 5,
    document_id: str | None = None
):
    """
    Search the authenticated user's document chunks
    using semantic similarity.
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not 1 <= match_count <= 20:
        raise ValueError("match_count must be between 1 and 20.")

    # 1. Convert user's question into an embedding
    query_embedding = generate_embedding(query.strip())

    # 2. Call Supabase PostgreSQL vector search function
    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_document_id": document_id
        }
    ).execute()

    return response.data
