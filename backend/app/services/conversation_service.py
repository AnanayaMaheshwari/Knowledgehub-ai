
from datetime import datetime, timezone
from uuid import UUID


def create_conversation(
    supabase,
    user_id: str,
    first_question: str
):
    """Create a new conversation for the authenticated user."""

    title = first_question.strip()[:60]

    if len(first_question.strip()) > 60:
        title += "..."

    response = (
        supabase.table("conversations")
        .insert({
            "user_id": user_id,
            "title": title
        })
        .select("id, title, created_at")
        .single()
        .execute()
    )

    if not response.data:
        raise RuntimeError("Failed to create conversation.")

    return response.data


def verify_conversation(
    supabase,
    conversation_id: UUID
):
    """Verify that the conversation exists and is accessible."""

    response = (
        supabase.table("conversations")
        .select("id, user_id, title")
        .eq("id", str(conversation_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Conversation not found or you do not have access to it."
        )

    return response.data


def save_message(
    supabase,
    conversation_id: UUID,
    role: str,
    content: str,
    sources: list | None = None
):
    """Save a user or assistant message."""

    if role not in ("user", "assistant"):
        raise ValueError("Invalid message role.")

    response = (
        supabase.table("messages")
        .insert({
            "conversation_id": str(conversation_id),
            "role": role,
            "content": content,
            "sources": sources or []
        })
        .select("id, conversation_id, role, content, sources, created_at")
        .single()
        .execute()
    )

    if not response.data:
        raise RuntimeError("Failed to save message.")

    return response.data


def update_conversation_timestamp(
    supabase,
    conversation_id: UUID
):
    """Update the conversation's last activity timestamp."""

    (
        supabase.table("conversations")
        .update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", str(conversation_id))
        .execute()
    )
