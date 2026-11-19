from app.core.security import get_current_user, get_current_user_supabase
from fastapi import APIRouter, HTTPException, Depends

from app.models.auth import (
    UserRegister,
    UserLogin,
    AuthResponse
)

from app.services.auth_service import (
    register_user,
    login_user
)



router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=AuthResponse)
def register(data: UserRegister):
    try:
        response = register_user(data.email, data.password)
        user = response.user

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Registration could not be completed."
            )

        return AuthResponse(
            message="Registration successful. Check your email if verification is required.",
            user_id=str(user.id),
            email=user.email
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Check your details or try again."
        )


@router.post("/login", response_model=AuthResponse)
def login(data: UserLogin):
    try:
        response = login_user(data.email, data.password)

        if not response.session or not response.user:
            raise HTTPException(
                status_code=401,
                detail="Login failed."
            )

        return AuthResponse(
            message="Login successful.",
            access_token=response.session.access_token,
            user_id=str(response.user.id),
            email=response.user.email
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "authenticated": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
        "message": "You are successfully authenticated."
    }

@router.get("/database-check")
def check_user_database_access(
    supabase=Depends(get_current_user_supabase)
):
    """
    Test database access using the logged-in user's JWT.
    Supabase RLS policies should apply to this query.
    """

    try:
        response = (
            supabase
            .table("documents")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "authenticated": True,
            "database_access": True,
            "visible_documents": len(response.data),
            "message": "User-scoped database query successful."
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="User-scoped database query failed."
        )
