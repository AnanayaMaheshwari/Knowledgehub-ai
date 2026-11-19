
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import (
    get_current_user,
    get_current_user_supabase
)

from app.models.chat import ChatQuestion, ChatResponse

from app.services.rag_service import answer_question

from app.services.llm_service import (
    classify_message,
    generate_chat_response
)

from app.services.conversation_service import (
    create_conversation,
    verify_conversation,
    save_message,
    update_conversation_timestamp
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# --------------------------------------------------
# CONVERSATION HISTORY
# --------------------------------------------------

def get_conversation_history(
    supabase,
    conversation_id: UUID,
    limit: int = 8
) -> list[dict]:
    """Fetch the latest messages in chronological order."""

    response = (
        supabase.table("messages")
        .select("role, content")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    messages = response.data or []

    return list(reversed(messages))


# --------------------------------------------------
# ASK QUESTION
# --------------------------------------------------

@router.post("/ask", response_model=ChatResponse)
def ask_question(
    request: ChatQuestion,
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    try:

        # Step 1: Find an existing conversation or create a new one.

        if request.conversation_id:

            try:
                conversation = verify_conversation(
                    supabase=supabase,
                    conversation_id=request.conversation_id
                )

            except ValueError:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found or access denied."
                )

            conversation_id = UUID(str(conversation["id"]))

            # Retrieve previous messages.
            conversation_history = get_conversation_history(
                supabase=supabase,
                conversation_id=conversation_id,
                limit=8
            )

        else:

            conversation = create_conversation(
                supabase=supabase,
                user_id=str(current_user.id),
                first_question=request.question
            )

            conversation_id = UUID(str(conversation["id"]))

            conversation_history = []


        # Step 2: Classify the latest message.

        message_type = classify_message(
            question=request.question,
            conversation_history=conversation_history
        )


        # Step 3: Generate the response using the appropriate mode.

        if message_type == "chat":

            # General chatbot mode.
            answer = generate_chat_response(
                question=request.question,
                conversation_history=conversation_history
            )

            sources = []

        else:

            # Document knowledge / RAG mode.
            result = answer_question(
                supabase=supabase,
                question=request.question,
                match_count=request.match_count,
                document_id=(
                    str(request.document_id)
                    if request.document_id
                    else None
                ),
                conversation_history=conversation_history
            )

            answer = result["answer"]
            sources = result.get("sources", [])


        # Step 4: Normalize source data.

        normalized_sources = [
            source.model_dump(mode="json")
            if hasattr(source, "model_dump")
            else source
            for source in sources
        ]


        # Step 5: Save the user's question.

        save_message(
            supabase=supabase,
            conversation_id=conversation_id,
            role="user",
            content=request.question
        )


        # Step 6: Save the assistant's response and citations.

        save_message(
            supabase=supabase,
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            sources=normalized_sources
        )


        # Step 7: Update conversation activity.

        update_conversation_timestamp(
            supabase=supabase,
            conversation_id=conversation_id
        )


        # Step 8: Return the response.

        return {
            "answer": answer,
            "sources": normalized_sources,
            "conversation_id": conversation_id
        }


    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        logger.exception(
            "Chat request failed for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process your question right now."
        )


# --------------------------------------------------
# GET ALL CONVERSATIONS
# --------------------------------------------------

@router.get("/conversations")
def get_conversations(
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    """Get all conversations belonging to the logged-in user."""

    try:

        response = (
            supabase.table("conversations")
            .select("id, title, created_at, updated_at")
            .order("updated_at", desc=True)
            .execute()
        )

        return {
            "total": len(response.data or []),
            "conversations": response.data or []
        }

    except Exception:
        logger.exception(
            "Failed to fetch conversations for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve conversations."
        )


# --------------------------------------------------
# GET CONVERSATION MESSAGES
# --------------------------------------------------

@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: UUID,
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    """Get messages belonging to a specific conversation."""

    try:

        try:
            verify_conversation(
                supabase=supabase,
                conversation_id=conversation_id
            )

        except ValueError:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found or access denied."
            )

        response = (
            supabase.table("messages")
            .select(
                "id, conversation_id, role, content, sources, created_at"
            )
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=False)
            .execute()
        )

        return {
            "conversation_id": str(conversation_id),
            "total": len(response.data or []),
            "messages": response.data or []
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Failed to fetch messages for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve conversation messages."
        )


# --------------------------------------------------
# DELETE CONVERSATION
# --------------------------------------------------

@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    current_user=Depends(get_current_user),
    supabase=Depends(get_current_user_supabase)
):
    """Delete a conversation belonging to the authenticated user."""

    try:

        verify_conversation(
            supabase=supabase,
            conversation_id=conversation_id
        )

        response = (
            supabase.table("conversations")
            .delete()
            .eq("id", str(conversation_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found or access denied."
            )

        return {
            "message": "Conversation deleted successfully.",
            "conversation_id": str(conversation_id)
        }

    except HTTPException:
        raise

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found or access denied."
        )

    except Exception:
        logger.exception(
            "Failed to delete conversation for user %s",
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to delete conversation."
        )
