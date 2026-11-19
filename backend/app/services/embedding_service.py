
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Load the model once and reuse it.
_model = None


def get_embedding_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(
            MODEL_NAME,
            device="cpu"
        )

    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate a 384-dimensional embedding for one text."""

    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple text chunks."""

    if not texts:
        return []

    if any(not text.strip() for text in texts):
        raise ValueError("All texts must be non-empty.")

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        batch_size=16,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    return embeddings.tolist()
