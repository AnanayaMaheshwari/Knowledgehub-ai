from app.services.document_summary_service import summarize_document
from uuid import UUID, uuid4
import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile
)

from app.core.security import (
    get_current_user,
    get_current_user_supabase
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

BUCKET_NAME = "knowledgehub-documents"
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}


# --------------------------------------------------
# 1. Upload a document
# --------------------------------------------------

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    filename = (
        (file.filename or "")
        .replace("\\", "/")
        .split("/")[-1]
    )

    extension = (
        "." + filename.rsplit(".", 1)[-1].lower()
        if "." in filename else ""
    )

    if extension not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported."
        )

    file_bytes = await file.read(MAX_FILE_SIZE + 1)

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size cannot exceed 10 MB."
        )

    # Basic file signature validation.
    if extension == ".pdf" and not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file."
        )

    if extension == ".docx" and not file_bytes.startswith(b"PK"):
        raise HTTPException(
            status_code=400,
            detail="Invalid DOCX file."
        )

    user_id = str(current_user.id)

    # Each user gets their own private Storage folder.
    storage_path = f"{user_id}/{uuid4().hex}{extension}"

    content_type = ALLOWED_TYPES[extension]

    try:
        # Upload file to private Supabase Storage.
        supabase.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "upsert": "false"
            }
        )

        # Insert document metadata into PostgreSQL.
        response = (
            supabase
            .table("documents")
            .insert({
                "user_id": user_id,
                "filename": filename,
                "file_type": extension.lstrip("."),
                "file_size": len(file_bytes),
                "storage_path": storage_path,
                "status": "pending"
            })
            .execute()
        )

        return {
            "message": "Document uploaded successfully.",
            "document": response.data[0] if response.data else None
        }

    except Exception:
        logger.exception(
            "Document upload failed for user %s",
            user_id
        )

        # Remove Storage object if database insertion fails.
        try:
            supabase.storage.from_(BUCKET_NAME).remove(
                [storage_path]
            )
        except Exception:
            logger.exception(
                "Storage cleanup failed for %s",
                storage_path
            )

        raise HTTPException(
            status_code=500,
            detail="Document upload failed. Please try again."
        )


# --------------------------------------------------
# 2. Retry a failed document
# --------------------------------------------------

@router.post("/{document_id}/retry", status_code=202)
def retry_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    try:
        response = supabase.rpc(
            "reset_document_retry",
            {
                "p_document_id": str(document_id)
            }
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Failed document not found or cannot be retried."
            )

        return {
            "message": "Document retry reset successfully.",
            "document_id": str(document_id),
            "status": "pending"
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Document retry failed for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Could not reset document retry. Please try again."
        )


# --------------------------------------------------
# 3. Count document chunks belonging to current user
# --------------------------------------------------

@router.get("/chunks/count")
def count_document_chunks(
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    try:
        response = (
            supabase
            .table("document_chunks")
            .select("id", count="exact", head=True)
            .execute()
        )

        total_chunks = response.count or 0

        return {
            "total_chunks": total_chunks
        }

    except Exception:
        logger.exception(
            "Could not count document chunks for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve your knowledge chunk count."
        )


# --------------------------------------------------
# 4. List documents with individual chunk counts
# --------------------------------------------------


# --------------------------------------------------
# 4. List documents with optimized chunk counts
# --------------------------------------------------

from time import perf_counter


@router.get("/")
def list_documents(
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    start_time = perf_counter()

    try:
        # Retrieve documents and their chunk counts
        # together using one database request.
        response = (
            supabase
            .table("documents")
            .select(
                """
                id,
                filename,
                file_type,
                file_size,
                status,
                created_at,
                document_chunks(count)
                """
            )
            .order("created_at", desc=True)
            .execute()
        )

        documents = response.data or []

        # Convert the embedded count into a simple integer.
        for document in documents:
            chunk_data = document.pop("document_chunks", [])

            document["chunk_count"] = (
                int(chunk_data[0]["count"])
                if chunk_data else 0
            )

        elapsed = perf_counter() - start_time

        logger.info(
            "Document listing completed: user=%s, documents=%s, time=%.3fs",
            current_user.id,
            len(documents),
            elapsed
        )

        return {
            "total": len(documents),
            "documents": documents
        }

    except Exception:
        logger.exception(
            "Could not retrieve documents for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve your documents."
        )


# --------------------------------------------------
# 5. Delete a document and its Storage file
# --------------------------------------------------

@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    try:
        # Call the secure database function.
        # It verifies ownership and prevents deletion during processing.
        response = supabase.rpc(
            "delete_document_for_user",
            {
                "p_document_id": str(document_id)
            }
        ).execute()

        result = response.data

        if not result or not result.get("deleted"):
            reason = result.get("reason") if result else None

            if reason == "processing":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This document is currently being processed. "
                        "Please try again later."
                    )
                )

            raise HTTPException(
                status_code=404,
                detail=(
                    "Document not found or you do not have "
                    "permission to delete it."
                )
            )

        # The database row and its chunks have been deleted.
        # Now remove the original file from private Storage.
        storage_path = result.get("storage_path")

        if not storage_path:
            logger.error(
                "Document %s was deleted but no Storage path was returned.",
                document_id
            )

            return {
                "message": "Document record deleted, but its Storage path was unavailable.",
                "document_id": str(document_id),
                "storage_cleanup": False
            }

        try:
            supabase.storage.from_(BUCKET_NAME).remove(
                [storage_path]
            )

            return {
                "message": (
                    "Document and its associated file "
                    "deleted successfully."
                ),
                "document_id": str(document_id),
                "storage_cleanup": True
            }

        except Exception:
            logger.exception(
                "Storage cleanup failed after deleting document %s "
                "for user %s",
                document_id,
                current_user.id
            )

            return {
                "message": (
                    "Document record and chunks deleted, but the "
                    "Storage file could not be removed."
                ),
                "document_id": str(document_id),
                "storage_cleanup": False
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Document deletion failed for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Could not delete the document. Please try again."
        )
@router.post("/{document_id}/summarize")
def summarize_uploaded_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    try:
        result = summarize_document(
            supabase=supabase,
            document_id=str(document_id)
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate document summary."
        )