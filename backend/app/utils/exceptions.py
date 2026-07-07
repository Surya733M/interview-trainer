"""
exceptions.py — Custom Application Exceptions
==============================================
Defines domain-specific exceptions that map to HTTP status codes.

Why custom exceptions?
  - Makes error handling readable: `raise ResumeParseError("No text found")`
  - FastAPI exception handlers convert them to proper HTTP responses automatically
  - Avoids catching generic Exception everywhere

Usage:
    from app.utils.exceptions import AuthenticationError
    raise AuthenticationError("Invalid credentials")
"""

from fastapi import HTTPException, status


# ── Authentication & Authorisation ────────────────────────────────────────────

class AuthenticationError(HTTPException):
    """Raised when login credentials are invalid or token is expired."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},  # Standard auth header
        )


class PermissionDeniedError(HTTPException):
    """Raised when a user tries to access a resource they don't own."""
    def __init__(self, detail: str = "You do not have permission to access this resource"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ── Resource Errors ───────────────────────────────────────────────────────────

class NotFoundError(HTTPException):
    """Raised when a database record or file is not found."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class AlreadyExistsError(HTTPException):
    """Raised when trying to create a resource that already exists (e.g., duplicate email)."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} already exists",
        )


# ── File & Resume Errors ──────────────────────────────────────────────────────

class InvalidFileTypeError(HTTPException):
    """Raised when uploaded file is not a PDF."""
    def __init__(self, detail: str = "Only PDF files are allowed"):
        super().__init__(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=detail)


class FileTooLargeError(HTTPException):
    """Raised when uploaded file exceeds the size limit."""
    def __init__(self, max_mb: int = 10):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {max_mb} MB",
        )


class ResumeParseError(HTTPException):
    """Raised when PyMuPDF cannot extract text from a PDF."""
    def __init__(self, detail: str = "Failed to parse resume PDF"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


# ── AI / RAG Errors ───────────────────────────────────────────────────────────

class GraniteAPIError(HTTPException):
    """Raised when the IBM watsonx.ai API call fails."""
    def __init__(self, detail: str = "IBM Granite API call failed"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class EmbeddingError(HTTPException):
    """Raised when text embedding generation fails."""
    def __init__(self, detail: str = "Failed to generate text embeddings"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class VectorSearchError(HTTPException):
    """Raised when ChromaDB similarity search fails."""
    def __init__(self, detail: str = "Vector search failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# ── Validation Errors ─────────────────────────────────────────────────────────

class ValidationError(HTTPException):
    """Raised when input data fails business logic validation (beyond Pydantic)."""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
