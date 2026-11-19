
import httpx
from supabase import create_client
from supabase.client import ClientOptions

from app.core.config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPABASE_SECRET_KEY
)


def get_supabase_client():
    """Create a normal Supabase client using the publishable key."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


def get_user_supabase_client(access_token: str):
    """Create a Supabase client using the authenticated user's JWT."""

    if not access_token:
        raise ValueError("Access token is required.")

    options = ClientOptions(
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )

    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )


def get_worker_supabase_client():
    """Create a privileged client exclusively for background processing."""

    if not SUPABASE_SECRET_KEY:
        raise ValueError(
            "SUPABASE_SECRET_KEY is missing. Check backend/.env"
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY
    )


def check_supabase_connection():
    """Check whether Supabase Auth API is reachable."""

    response = httpx.get(
        f"{SUPABASE_URL}/auth/v1/health",
        headers={"apikey": SUPABASE_KEY},
        timeout=10
    )

    response.raise_for_status()
    return True


def check_database_connection():
    """Test a database query through the normal Supabase client."""

    supabase = get_supabase_client()

    response = (
        supabase.table("documents")
        .select("id")
        .limit(1)
        .execute()
    )

    return True
