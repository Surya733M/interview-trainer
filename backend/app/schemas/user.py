"""
schemas/user.py — User Request/Response Schemas
=================================================
Pydantic models define the exact shape of data at the API boundary.

Why separate schemas from ORM models?
  - ORM model = database shape (has hashed_password, internal fields)
  - Schema     = API shape     (never exposes hashed_password to clients)
  - This separation is a security best practice

Schema naming convention:
  UserCreate   → input when registering (email + password)
  UserLogin    → input when logging in
  UserResponse → output returned to client (never includes password)
  Token        → JWT token returned after login
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


# ── Registration ──────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """
    Data required to register a new account.
    EmailStr automatically validates the email format.
    Field(..., min_length=8) ensures password is at least 8 characters.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: Optional[str] = Field(None, max_length=100)


# ── Login ─────────────────────────────────────────────────────────────────────
class UserLogin(BaseModel):
    """Data required to authenticate an existing user."""
    email: EmailStr
    password: str


# ── Response (safe to send to client) ────────────────────────────────────────
class UserResponse(BaseModel):
    """
    What we return to the client after registration or profile fetch.
    Notice: hashed_password is intentionally NOT included.
    """
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    # model_config with from_attributes=True allows Pydantic to read data
    # directly from SQLAlchemy ORM objects (not just plain dicts)
    model_config = {"from_attributes": True}


# ── JWT Token Response ────────────────────────────────────────────────────────
class Token(BaseModel):
    """Returned to the client after successful login."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Internal representation of decoded JWT payload."""
    user_id: Optional[int] = None
    email: Optional[str] = None


# ── Auth Response (token + user info combined) ────────────────────────────────
class AuthResponse(BaseModel):
    """Single response containing both the token and user profile."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
