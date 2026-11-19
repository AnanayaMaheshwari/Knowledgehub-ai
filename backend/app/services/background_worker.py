
import asyncio
import logging
from uuid import uuid4

from app.services.supabase_service import get_worker_supabase_client
from app.services.document_ingestion_service import (
    process_claimed_document_for_worker
)


logger = logging.getLogger(__name__)

POLL_INTERVAL = 5
LEASE_RENEW_INTERVAL = 60


async def renew_processing_lease(
    supabase,
    document_id: str,
    processing_token: str
):
    """Extend the active document processing lease."""

    response = await asyncio.to_thread(
        lambda: supabase.rpc(
            "renew_document_processing_lease_for_worker",
            {
                "p_document_id": document_id,
                "p_processing_token": processing_token
            }
        ).execute()
    )

    if response.data is not True:
        raise RuntimeError(
            f"Could not renew processing lease for {document_id}"
        )


async def lease_heartbeat(
    supabase,
    document_id: str,
    processing_token: str
):
    """
    Renew the lease periodically while a document is processing.
    """

    while True:
        await asyncio.sleep(LEASE_RENEW_INTERVAL)

        try:
            await renew_processing_lease(
                supabase,
                document_id,
                processing_token
            )

            logger.info(
                "Processing lease renewed for document %s",
                document_id
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Processing lease renewal failed for document %s",
                document_id
            )
            return


async def process_one_document(supabase):
    """Claim and process one pending document."""

    processing_token = str(uuid4())

    # Step 1: Claim a document atomically.
    claim_response = await asyncio.to_thread(
        lambda: supabase.rpc(
            "claim_next_document_for_worker",
            {
                "p_processing_token": processing_token
            }
        ).execute()
    )

    claimed_documents = claim_response.data

    if not claimed_documents:
        return False

    document = claimed_documents[0]
    document_id = document["claimed_document_id"]

    logger.info(
        "Claimed document: %s",
        document["claimed_filename"]
    )

    # Step 2: Start automatic lease renewal.
    heartbeat_task = asyncio.create_task(
        lease_heartbeat(
            supabase,
            document_id,
            processing_token
        )
    )

    try:
        # Step 3: Process the document in a background thread.
        result = await asyncio.to_thread(
            process_claimed_document_for_worker,
            supabase,
            document,
            processing_token
        )

        logger.info(
            "Document processed successfully: %s",
            result["filename"]
        )

    except asyncio.CancelledError:
        logger.warning(
            "Processing task cancelled for document %s. "
            "Its lease will expire if processing cannot finish.",
            document_id
        )
        raise

    except Exception:
        logger.exception(
            "Document processing failed: %s",
            document["claimed_filename"]
        )

    finally:
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

    return True


async def background_worker():
    """Continuously poll Supabase for documents to process."""

    logger.info("KnowledgeHub AI background worker started.")

    supabase = get_worker_supabase_client()

    while True:
        try:
            document_found = await process_one_document(supabase)

            if not document_found:
                await asyncio.sleep(POLL_INTERVAL)

        except asyncio.CancelledError:
            logger.info("Background worker is shutting down.")
            raise

        except Exception:
            logger.exception(
                "Background worker encountered an unexpected error."
            )

            await asyncio.sleep(POLL_INTERVAL)
