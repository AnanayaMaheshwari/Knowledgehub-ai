
import logging
from time import perf_counter

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

from app.services.supabase_service import (
    get_supabase_client,
    get_user_supabase_client
)


logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# --------------------------------------------------
# 1. VERIFY CURRENT USER
# --------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
):
    """
    Verify the access token with Supabase
    and return the authenticated user.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    try:
        auth_start = perf_counter()

        try:
            supabase = get_supabase_client()
            response = supabase.auth.get_user(token)

        finally:
            auth_elapsed = perf_counter() - auth_start

            logger.info(
                "Authentication verification completed in %.3fs",
                auth_elapsed
            )

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token."
            )

        return response.user

    except HTTPException:
        raise

    except Exception:
        logger.exception("Authentication verification failed")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )


# --------------------------------------------------
# 2. GET AUTHENTICATED USER SUPABASE CLIENT
# --------------------------------------------------

def get_current_user_supabase(
    current_user=Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
):
    """
    Return a Supabase client authenticated as the current user.

    get_current_user verifies the JWT before this client is created.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )

    return get_user_supabase_client(credentials.credentials)
