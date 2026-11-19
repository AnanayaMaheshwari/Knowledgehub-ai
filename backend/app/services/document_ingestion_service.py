
import json
from uuid import uuid4

from app.services.document_processor import extract_document_text
from app.services.text_chunker import create_document_chunks
from app.services.embedding_service import generate_embeddings


BUCKET_NAME = "knowledgehub-documents"


# ============================================================
# 1. USER-SCOPED DOCUMENT PROCESSING
# ============================================================

def process_document(supabase, document_id: str):
    """
    Download, extract, chunk, embed and save a document.

    The supplied Supabase client must be user-scoped.
    """

    # Step 1: Retrieve document metadata.
    response = (
        supabase.table("documents")
        .select("id, filename, file_type, storage_path")
        .eq("id", document_id)
        .single()
        .execute()
    )

    document = response.data

    # Step 2: Generate a unique processing token.
    processing_token = str(uuid4())

    # Step 3: Atomically claim the document.
    claim_response = supabase.rpc(
        "claim_document_processing",
        {
            "p_document_id": document_id,
            "p_processing_token": processing_token
        }
    ).execute()

    if not claim_response.data:
        raise RuntimeError(
            "Document cannot be processed. It may already be processing "
            "or may have reached its retry limit."
        )

    try:
        # Step 4: Download the original file.
        file_bytes = (
            supabase.storage
            .from_(BUCKET_NAME)
            .download(document["storage_path"])
        )

        # Step 5: Extract text.
        extracted_text = extract_document_text(
            file_bytes,
            document["file_type"]
        )

        if not extracted_text.strip():
            raise ValueError("No readable text found in the document.")

        # Step 6: Create chunks.
        chunks = create_document_chunks(extracted_text)

        if not chunks:
            raise ValueError("No text chunks were generated.")

        # Step 7: Generate embeddings.
        texts = [chunk["content"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count."
            )

        # Step 8: Prepare chunk records.
        records = []

        for chunk, embedding in zip(chunks, embeddings):
            records.append({
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "embedding_text": json.dumps(embedding),
                "metadata": {}
            })

        # Step 9: Atomically replace chunks.
        replacement_response = supabase.rpc(
            "replace_document_chunks",
            {
                "p_document_id": document_id,
                "p_processing_token": processing_token,
                "p_chunks": records
            }
        ).execute()

        inserted_count = replacement_response.data

        if inserted_count != len(chunks):
            raise RuntimeError(
                f"Expected {len(chunks)} chunks, "
                f"but database inserted {inserted_count}."
            )

        # Step 10: Mark document completed.
        completion_response = (
            supabase.table("documents")
            .update({
                "status": "completed",
                "error_message": None,
                "retry_count": 0,
                "processing_token": None,
                "processing_lease_until": None
            })
            .eq("id", document_id)
            .eq("processing_token", processing_token)
            .select("id")
            .execute()
        )

        if not completion_response.data:
            raise RuntimeError(
                "Processing finished, but this worker no longer "
                "owns the processing lease."
            )

        return {
            "message": "Document processed successfully.",
            "document_id": document_id,
            "filename": document["filename"],
            "total_chunks": len(chunks),
            "total_embeddings": len(embeddings),
            "inserted_chunks": inserted_count
        }

    except Exception as error:
        # Record failure only if this worker owns the document.
        try:
            supabase.rpc(
                "fail_document_processing",
                {
                    "p_document_id": document_id,
                    "p_processing_token": processing_token,
                    "p_error_message": str(error)[:1000]
                }
            ).execute()

        except Exception as failure_error:
            print(
                "Could not record document processing failure:",
                failure_error
            )

        raise


# ============================================================
# 2. BACKGROUND WORKER DOCUMENT PROCESSING
# ============================================================

def process_claimed_document_for_worker(
    supabase,
    document: dict,
    processing_token: str
):
    """
    Process a document already claimed by the background worker.

    The supplied Supabase client must use the secret key.

    The worker must already own the document's processing lease.
    """

    document_id = document["claimed_document_id"]
    filename = document["claimed_filename"]
    file_type = document["claimed_file_type"]
    storage_path = document["claimed_storage_path"]

    try:
        # Step 1: Download the original document.
        file_bytes = (
            supabase.storage
            .from_(BUCKET_NAME)
            .download(storage_path)
        )

        # Step 2: Extract document text.
        extracted_text = extract_document_text(
            file_bytes,
            file_type
        )

        if not extracted_text.strip():
            raise ValueError("No readable text found in the document.")

        # Step 3: Create text chunks.
        chunks = create_document_chunks(extracted_text)

        if not chunks:
            raise ValueError("No text chunks were generated.")

        # Step 4: Generate embeddings.
        texts = [chunk["content"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count."
            )

        # Step 5: Prepare chunk records.
        records = []

        for chunk, embedding in zip(chunks, embeddings):
            records.append({
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "embedding_text": json.dumps(embedding),
                "metadata": {}
            })

        # Step 6: Renew the processing lease.
        lease_response = supabase.rpc(
            "renew_document_processing_lease_for_worker",
            {
                "p_document_id": document_id,
                "p_processing_token": processing_token
            }
        ).execute()

        if lease_response.data is not True:
            raise RuntimeError(
                "Processing lease expired or is no longer owned."
            )

        # Step 7: Replace chunks atomically.
        replacement_response = supabase.rpc(
            "replace_document_chunks_for_worker",
            {
                "p_document_id": document_id,
                "p_processing_token": processing_token,
                "p_chunks": records
            }
        ).execute()

        inserted_count = replacement_response.data

        if inserted_count != len(chunks):
            raise RuntimeError(
                f"Expected {len(chunks)} chunks, "
                f"but inserted {inserted_count}."
            )

        # Step 8: Mark document completed.
        completion_response = supabase.rpc(
            "complete_document_processing_for_worker",
            {
                "p_document_id": document_id,
                "p_processing_token": processing_token
            }
        ).execute()

        if not completion_response.data:
            raise RuntimeError(
                "Could not complete document processing. "
                "The processing lease may have expired."
            )

        return {
            "message": "Document processed successfully.",
            "document_id": document_id,
            "filename": filename,
            "total_chunks": len(chunks),
            "total_embeddings": len(embeddings),
            "inserted_chunks": inserted_count
        }

    except Exception as error:
        # Record failure only if this worker owns the active lease.
        try:
            supabase.rpc(
                "fail_document_processing_for_worker",
                {
                    "p_document_id": document_id,
                    "p_processing_token": processing_token,
                    "p_error_message": str(error)[:1000]
                }
            ).execute()

        except Exception as failure_error:
            print(
                "Could not record worker processing failure:",
                failure_error
            )

        raise
