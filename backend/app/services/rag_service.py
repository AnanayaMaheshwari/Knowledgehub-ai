
from app.services.search_service import search_documents
from app.services.llm_service import (
    generate_answer,
    rewrite_search_query
)


# Initial threshold. We will tune this using real test questions.
MIN_SIMILARITY = 0.35


def answer_question(
    supabase,
    question: str,
    match_count: int = 5,
    document_id: str | None = None,
    conversation_history: list[dict] | None = None
):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    # Step 1: Rewrite follow-up questions for better retrieval.
    if conversation_history:
        retrieval_query = rewrite_search_query(
            question=question.strip(),
            conversation_history=conversation_history
        )
    else:
        retrieval_query = question.strip()

    # Step 2: Retrieve relevant document chunks.
    results = search_documents(
        supabase=supabase,
        query=retrieval_query,
        match_count=match_count,
        document_id=document_id
    )

    # Step 3: Filter out low-relevance chunks.
    relevant_results = [
        result for result in results
        if result["similarity"] >= MIN_SIMILARITY
    ]

    if not relevant_results:
        return {
            "answer": (
                "I couldn't find sufficiently relevant information "
                "in your uploaded documents to answer this question."
            ),
            "sources": []
        }

    # Step 4: Fetch document filenames.
    document_ids = list({
        result["document_id"]
        for result in relevant_results
    })

    document_response = (
        supabase.table("documents")
        .select("id, filename")
        .in_("id", document_ids)
        .execute()
    )

    documents = {
        doc["id"]: doc["filename"]
        for doc in document_response.data
    }

    # Step 5: Prepare document context and source metadata.
    context_parts = []
    sources = []

    for index, result in enumerate(relevant_results, start=1):
        source_label = f"[{index}]"

        filename = documents.get(
            result["document_id"],
            "Unknown document"
        )

        context_parts.append(
            f"""
Source {source_label}
Document: {filename}
Page: {result["page_number"]}
Content:
{result["content"]}
"""
        )

        sources.append({
            "source_label": source_label,
            "document_id": result["document_id"],
            "filename": filename,
            "page_number": result["page_number"],
            "chunk_index": result["chunk_index"],
            "similarity": round(result["similarity"], 4)
        })

    context = "\n\n".join(context_parts)

    # Step 6: Generate an answer using documents and conversation history.
    answer = generate_answer(
        question=question.strip(),
        context=context,
        conversation_history=conversation_history
    )

    return {
        "answer": answer,
        "sources": sources
    }
