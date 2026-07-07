"""
services/section_extractor.py — Resume Section Detection
==========================================================
After PyMuPDF gives us raw text, this module splits the text
into labelled sections: Education, Experience, Skills, etc.

How it works:
  - A resume typically has section headers like "EDUCATION", "Skills", "Work Experience"
  - We search for these headers using regex (case-insensitive)
  - Everything between two headers belongs to the first header's section
  - Returns a dict: { "education": "...", "experience": "...", ... }

This is used by skill_extractor.py (Step 9) to extract structured data
from the correct section rather than the entire text.
"""

import re
from typing import Dict, List
from app.utils.logger import logger


# ── Section header keyword patterns ──────────────────────────────────────────
# Each key maps to a list of regex patterns that identify that section header.
# We use (?i) for case-insensitive matching.
# \b = word boundary so "skills" doesn't match "unskilled"

SECTION_PATTERNS: Dict[str, List[str]] = {
    "contact": [
        r"\b(contact|personal\s+info|personal\s+details|contact\s+information)\b"
    ],
    "summary": [
        r"\b(summary|objective|profile|about\s+me|career\s+objective|professional\s+summary)\b"
    ],
    "education": [
        r"\b(education|academic|qualifications?|degrees?|schooling|university|college)\b"
    ],
    "experience": [
        r"\b(experience|work\s+experience|employment|work\s+history|professional\s+experience|internship|career)\b"
    ],
    "skills": [
        r"\b(skills?|technical\s+skills?|core\s+competenc|technologies|tools|programming|languages?)\b"
    ],
    "projects": [
        r"\b(projects?|personal\s+projects?|academic\s+projects?|key\s+projects?|portfolio)\b"
    ],
    "certifications": [
        r"\b(certifications?|certificates?|courses?|training|achievements?|awards?)\b"
    ],
    "hobbies": [
        r"\b(hobbies|interests?|activities|extra.?curricular)\b"
    ],
}


def extract_sections(resume_text: str) -> Dict[str, str]:
    """
    Split resume text into labelled sections.

    Args:
        resume_text: full text extracted from the PDF

    Returns:
        dict mapping section name → section text content
        e.g. {"education": "B.Tech...", "skills": "Python, React..."}
    """
    lines = resume_text.split('\n')
    sections: Dict[str, str] = {}
    current_section = "header"    # text before first recognised header
    current_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_lines.append('')
            continue

        # Check if this line is a section header
        detected = _detect_section_header(stripped)

        if detected:
            # Save the previous section
            if current_lines:
                sections[current_section] = '\n'.join(current_lines).strip()
            # Start the new section
            current_section = detected
            current_lines = []
        else:
            current_lines.append(stripped)

    # Save the last section
    if current_lines:
        sections[current_section] = '\n'.join(current_lines).strip()

    logger.debug(f"Detected resume sections: {list(sections.keys())}")
    return sections


def _detect_section_header(line: str) -> str | None:
    """
    Check if a line is a section header.

    Heuristics:
      1. The line is short (< 60 chars) — headers are rarely long sentences
      2. It matches one of our section keyword patterns
      3. It may be ALL CAPS or Title Case

    Returns the section name if matched, None otherwise.
    """
    # Skip very long lines — they're likely body text, not headers
    if len(line) > 60:
        return None

    line_lower = line.lower()

    for section_name, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, line_lower, re.IGNORECASE):
                return section_name

    return None


def get_candidate_name(resume_text: str) -> str:
    """
    Attempt to extract the candidate's name from the resume.

    Strategy:
      - The name is usually the first non-empty line of the resume
      - It should be 2-4 words, mostly alphabetic
      - Not a common header word

    Returns empty string if name cannot be determined.
    """
    lines = [l.strip() for l in resume_text.split('\n') if l.strip()]

    # Skip common headers that appear first in some templates
    skip_words = {'resume', 'cv', 'curriculum', 'vitae', 'profile', 'contact'}

    for line in lines[:5]:   # only look at first 5 lines
        words = line.split()
        # Name: 2-5 words, mostly alphabetic, not a section header
        if 2 <= len(words) <= 5:
            if all(re.match(r"^[A-Za-z.'\-]+$", w) for w in words):
                if not any(w.lower() in skip_words for w in words):
                    return line

    return ""
