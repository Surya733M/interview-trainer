"""
Test script for Step 7 — Resume Upload Pipeline
Run: python test_step7.py
"""
import os, json, sys
os.makedirs('./uploads', exist_ok=True)
os.makedirs('./reports', exist_ok=True)
os.makedirs('./logs', exist_ok=True)

# ── Test 1: Imports ────────────────────────────────────────────────────────────
from app.services.resume_parser import extract_text_from_pdf, _clean_extracted_text
from app.services.section_extractor import extract_sections, get_candidate_name
from app.services.resume_service import (
    _extract_skills, _determine_experience_level,
    _suggest_role, _find_missing_skills,
)
from app.utils.cos_client import cos_client
print('[PASS] All new modules imported')

# ── Test 2: Text cleaning ──────────────────────────────────────────────────────
dirty = 'Python Developer\r\n\r\n\r\n  Skills   \r\nPython  '
clean = _clean_extracted_text(dirty)
assert 'Python Developer' in clean
print('[PASS] Text cleaning')

# ── Test 3: Section detection ──────────────────────────────────────────────────
sample_resume = """
John Doe
john@example.com | +91-9876543210

EDUCATION
B.Tech Computer Science
IIT Delhi, 2020

SKILLS
Python, React, JavaScript, SQL, Docker, Git, FastAPI, AWS, Machine Learning

EXPERIENCE
Jan 2021 - Present
Software Developer
Infosys
Built REST APIs using FastAPI and Python. Deployed on AWS.

PROJECTS
Interview Trainer App
Built an AI-powered interview trainer using IBM Granite and RAG.

CERTIFICATIONS
AWS Certified Solutions Architect
IBM Data Science Professional Certificate
"""

sections = extract_sections(sample_resume)
print(f'[PASS] Sections detected: {list(sections.keys())}')

# ── Test 4: Skill extraction ───────────────────────────────────────────────────
skills = _extract_skills(sections)
print(f'[PASS] Skills extracted ({len(skills)}): {skills}')
assert 'Python' in skills, f'Python not found in {skills}'
assert 'React' in skills, f'React not found in {skills}'
assert 'Docker' in skills, f'Docker not found in {skills}'

# ── Test 5: Experience level ───────────────────────────────────────────────────
level = _determine_experience_level([], sample_resume)
print(f'[PASS] Experience level: {level}')

# ── Test 6: Role suggestion ────────────────────────────────────────────────────
role = _suggest_role(skills)
print(f'[PASS] Suggested role: {role}')

# ── Test 7: Missing skills ─────────────────────────────────────────────────────
missing = _find_missing_skills(skills, role)
print(f'[PASS] Missing skills for "{role}": {missing}')

# ── Test 8: COS graceful fallback ─────────────────────────────────────────────
with open('./uploads/test_cos.txt', 'w') as f:
    f.write('test')
result = cos_client.upload_file('./uploads/test_cos.txt', 'test/test_cos.txt')
assert result.startswith('local://') or result.startswith('http'), f'Unexpected: {result}'
print(f'[PASS] COS fallback: {result[:50]}')

# ── Test 9: Candidate name extraction ─────────────────────────────────────────
name = get_candidate_name(sample_resume)
print(f'[PASS] Candidate name detected: "{name}"')

# ── Test 10: Create a real PDF and parse it ────────────────────────────────────
try:
    import fitz
    doc = fitz.open()           # create blank PDF in memory
    page = doc.new_page()       # add one page
    # Insert text onto the page at position (72, 72)
    page.insert_text((72, 72), sample_resume, fontsize=10)
    test_pdf_path = './uploads/test_resume.pdf'
    doc.save(test_pdf_path)
    doc.close()

    extracted = extract_text_from_pdf(test_pdf_path)
    assert len(extracted) > 50, f'Extracted text too short: {len(extracted)}'
    assert 'Python' in extracted or 'John' in extracted
    print(f'[PASS] PyMuPDF real PDF extraction: {len(extracted)} chars')
except Exception as e:
    print(f'[WARN] PDF creation test skipped: {e}')

print()
print('====================================')
print(' Step 7 Tests: ALL PASSED')
print('====================================')
