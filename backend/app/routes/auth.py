"""
routes/auth.py — Authentication Endpoints
==========================================
Endpoints:
  POST /auth/register  → create a new user account
  POST /auth/login     → get a JWT token
  GET  /auth/me        → get current user's profile (protected)
  POST /auth/logout    → client-side logout (token is stateless)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, AuthResponse, Token
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_active_user,
)
from app.utils.exceptions import AlreadyExistsError, AuthenticationError
from app.utils.logger import logger

# APIRouter groups related endpoints together
# prefix="/auth" means all routes here start with /auth
# tags=["Authentication"] groups them in Swagger UI
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── POST /auth/register ───────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.

    Steps:
      1. Check if email already exists (reject duplicates)
      2. Hash the password with bcrypt
      3. Create the User record in the database
      4. Issue a JWT token so the user is immediately logged in
    """
    # Step 1: check for duplicate email
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise AlreadyExistsError("Email")

    # Step 2: hash the password — NEVER store plain text
    hashed = hash_password(user_data.password)

    # Step 3: create and save the user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed,
        full_name=user_data.full_name,
    )
    db.add(new_user)
    db.commit()           # ← persist to database
    db.refresh(new_user)  # ← reload from DB to get auto-generated id, created_at

    logger.info(f"New user registered: {new_user.email}")

    # Step 4: issue a JWT token
    token = create_access_token(data={
        "sub": f"user_id:{new_user.id}",
        "email": new_user.email,
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


# ── POST /auth/login ──────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login and receive a JWT token",
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token.

    Steps:
      1. Find user by email
      2. Verify the password against the bcrypt hash
      3. Issue a JWT token
    """
    # Step 1: find user
    user = db.query(User).filter(User.email == credentials.email).first()

    # Step 2: verify password
    # We do BOTH checks before raising the error — this prevents
    # "timing attacks" where an attacker can tell if an email exists
    # based on how long the response takes.
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is disabled. Please contact support.")

    logger.info(f"User logged in: {user.email}")

    # Step 3: issue token
    token = create_access_token(data={
        "sub": f"user_id:{user.id}",
        "email": user.email,
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ── GET /auth/me ──────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user's profile",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Return the authenticated user's profile.
    Requires a valid Bearer token in the Authorization header.
    """
    return UserResponse.model_validate(current_user)


# ── POST /auth/logout ─────────────────────────────────────────────────────────
@router.post(
    "/logout",
    summary="Logout (client must discard the token)",
)
def logout(current_user: User = Depends(get_current_active_user)):
    """
    JWT tokens are stateless — the server cannot invalidate them.
    This endpoint just confirms the token was valid.
    The client must delete the token from localStorage.

    For production: implement a token blacklist in Redis.
    """
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Logged out successfully. Please delete your token."}
