from app.services.supabase_service import get_supabase_client


def register_user(email: str, password: str):
    """Register a new user using Supabase Auth."""

    supabase = get_supabase_client()

    response = supabase.auth.sign_up({
        "email": email,
        "password": password
    })

    return response


def login_user(email: str, password: str):
    """Authenticate an existing user."""

    supabase = get_supabase_client()

    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

    return response