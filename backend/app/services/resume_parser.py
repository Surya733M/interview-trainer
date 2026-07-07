"""
services/resume_parser.py — PDF Text Extraction using PyMuPDF
==============================================================
PyMuPDF (imported as 'fitz') is the fastest and most accurate
open-source Python library for extracting text from PDFs.

Why PyMuPDF over alternatives?
  - pdfplumber  : slower, less accurate for complex layouts
  - pdfminer    : very low-level, requires much more code
  - PyMuPDF     : C-based, handles scanned PDFs, 10x faster

How PDF text extraction works:
  1. PDF is a container of "pages" (not just text)
  2. Each page contains text objects at specific coordinates
  3. PyMuPDF reads these objects and returns plain text
  4. We join all pages with newlines for a clean string

Usage:
    from app.services.resume_parser import extract_text_from_pdf
    text = extract_text_from_pdf("uploads/resume.pdf")
"""

import fitz          # PyMuPDF — imported as 'fitz' (historical name)
import os
import re
from typing import Optional

from app.utils.logger import logger
from app.utils.exceptions import ResumeParseError


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text from a PDF file using PyMuPDF.

    Args:
        file_path: absolute or relative path to the PDF file

    Returns:
        A single string containing all extracted text from all pages.
        Pages are separated by a newline + page marker.

    Raises:
        ResumeParseError: if the file is not readable or has no text
    """
    # Verify file exists before trying to open it
    if not os.path.exists(file_path):
        raise ResumeParseError(f"Resume file not found: {file_path}")

    try:
        # fitz.open() reads the PDF into memory
        doc = fitz.open(file_path)

        # Check the PDF is not empty
        if doc.page_count == 0:
            raise ResumeParseError("PDF has no pages")

        all_text_parts = []

        # Iterate through every page (0-indexed)
        for page_num in range(doc.page_count):
            page = doc[page_num]

            # get_text("text") extracts plain text in reading order.
            # Other options: "html", "dict", "blocks" — we use plain text.
            page_text = page.get_text("text")

            if page_text.strip():   # skip truly empty pages
                all_text_parts.append(page_text)

        # Always close the document to free memory
        doc.close()

        if not all_text_parts:
            raise ResumeParseError(
                "No readable text found in the PDF. "
                "If this is a scanned PDF, OCR is required."
            )

        # Join all pages with a separator
        full_text = "\n\n".join(all_text_parts)

        # Clean up excessive whitespace while preserving structure
        full_text = _clean_extracted_text(full_text)

        logger.info(
            f"Extracted {len(full_text)} characters from "
            f"{doc.page_count if hasattr(doc, 'page_count') else '?'} pages: {file_path}"
        )
        return full_text

    except ResumeParseError:
        raise   # re-raise our own exceptions unchanged
    except fitz.FileDataError as e:
        raise ResumeParseError(f"Corrupted or invalid PDF: {e}")
    except Exception as e:
        logger.error(f"PDF extraction failed for {file_path}: {e}")
        raise ResumeParseError(f"Could not read the PDF file. Please ensure it is a valid, non-corrupted PDF.")


def _clean_extracted_text(text: str) -> str:
    """
    Clean raw extracted text for downstream processing.

    Steps:
      1. Normalise line endings (PDFs can use \\r\\n or \\r)
      2. Remove excessive blank lines (>2 consecutive)
      3. Strip leading/trailing whitespace per line
      4. Remove non-printable characters (keeps Unicode letters)
    """
    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove non-printable characters except newlines and tabs
    text = re.sub(r'[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]', '', text)

    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip trailing spaces from each line
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def get_pdf_metadata(file_path: str) -> dict:
    """
    Extract PDF metadata (author, title, creation date).
    Useful for pre-filling candidate name if resume PDF has metadata.

    Returns:
        dict with keys: title, author, pages, file_size_kb
    """
    try:
        doc = fitz.open(file_path)
        meta = doc.metadata or {}
        pages = doc.page_count
        doc.close()

        file_size_kb = os.path.getsize(file_path) // 1024

        return {
            "title":        meta.get("title", ""),
            "author":       meta.get("author", ""),
            "pages":        pages,
            "file_size_kb": file_size_kb,
        }
    except Exception as e:
        logger.warning(f"Could not read PDF metadata: {e}")
        return {"title": "", "author": "", "pages": 0, "file_size_kb": 0}
