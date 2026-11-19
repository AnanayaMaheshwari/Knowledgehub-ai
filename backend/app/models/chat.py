
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ChatQuestion(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
        description="Your question about uploaded documents."
    )

    match_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of relevant document chunks to retrieve."
    )

    document_id: UUID | None = Field(
        default=None,
        description=(
            "Optional uploaded document ID. "
            "Leave empty to search all your accessible documents."
        )
    )

    conversation_id: UUID | None = Field(
        default=None,
        description=(
            "Optional conversation ID. "
            "Leave empty to create a new conversation."
        )
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "What is the minimum age requirement for a loan?",
                    "match_count": 5
                }
            ]
        }
    )


class ChatSource(BaseModel):
    source_label: str
    document_id: UUID
    filename: str
    page_number: int | None = None
    chunk_index: int
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)

    conversation_id: UUID | None = Field(
        default=None,
        description="ID of the conversation containing this exchange."
    )
