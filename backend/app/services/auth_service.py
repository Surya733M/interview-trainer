"""
services/auth_service.py — Authentication Business Logic
=========================================================
Handles:
  1. Password hashing with bcrypt (never store plain text passwords)
  2. JWT token creation (issued on login)
  3. JWT token verification (validates every protected API request)
  4. Current user extraction (FastAPI dependency)

Security concepts:
  bcrypt : one-way hashing — you can verify but never reverse it
  JWT    : JSON Web Token — a signed string proving who the user is
           Header.Payload.Signature (base64 encoded, period-separated)
           The Signature is created with your SECRET_KEY — only your server
           can create valid tokens, so clients cannot forge them.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenData
from app.utils.exceptions import AuthenticationError, NotFoundError
from app.utils.logger import logger

# ── Password Hashing ──────────────────────────────────────────────────────────
# CryptContext with bcrypt automatically:
#   - Hashes passwords using bcrypt (slow by design — resists brute force)
#   - Handles salt generation (random bytes mixed into the hash)
#   - Verifies passwords by re-hashing and comparing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 Bearer Token Scheme ────────────────────────────────────────────────
# This tells FastAPI where to look for the token.
# tokenUrl="/auth/login" is used by Swagger UI's "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Password Functions ─────────────────────────────────────────────────────────
def hash_password(plain_password: str) -> str:
    """
    Convert a plain text password into a bcrypt hash.
    The hash is a 60-character string that looks like:
      $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW
    It includes the algorithm, cost factor, salt, and hash — everything
    needed to verify a password later.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain text password matches the stored bcrypt hash.
    Returns True if they match, False otherwise.
    Never compares the plain text directly — always re-hashes and compares.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Functions ────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: dict with the claims to encode, e.g. {"sub": "user_id:42"}
        expires_delta: how long the token is valid (defaults to config value)

    Returns:
        A JWT string like: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

    The token payload (decoded) looks like:
        {
          "sub": "user_id:42",
          "exp": 1703012345    ← expiry timestamp
        }
    """
    to_encode = data.copy()

    # Set expiry time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    # Sign the token with SECRET_KEY using HS256 algorithm
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.

    Raises AuthenticationError if:
      - Token signature is invalid (tampered)
      - Token has expired
      - Token payload is malformed

    Returns TokenData with user_id and email if valid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        # "sub" is the JWT standard claim for "subject" (who the token is about)
        subject: str = payload.get("sub")
        if subject is None:
            raise AuthenticationError("Invalid token: missing subject")

        # We encode as "user_id:42 email:user@example.com"
        user_id = int(subject.split(":")[1])
        email   = payload.get("email")
        return TokenData(user_id=user_id, email=email)

    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        raise AuthenticationError("Token is invalid or has expired")


# ── FastAPI Dependencies ───────────────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts and validates the current user from the
    Authorization header on every protected route.

    Usage in any route:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}

    Flow:
      1. OAuth2PasswordBearer extracts the token from "Authorization: Bearer <token>"
      2. decode_access_token verifies the signature and expiry
      3. We look up the user in the database
      4. We verify the account is still active
    """
    token_data = decode_access_token(token)

    # Look up user in database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Convenience dependency — same as get_current_user but named semantically."""
    return current_user
