"""
prompts/question_gen.py — Interview Question Generation Prompts
================================================================
Prompt templates for IBM Granite to generate personalised interview questions.

Each prompt is a carefully crafted instruction that:
  1. Gives Granite the candidate's context (resume, skills, level)
  2. Provides retrieved RAG context (relevant interview documents)
  3. Instructs Granite to output STRICTLY valid JSON
  4. Specifies exact question types and counts
"""


def build_question_generation_prompt(
    job_title:       str,
    skills:          list[str],
    experience_level: str,
    resume_summary:  str,
    rag_context:     str,
    num_technical:   int = 5,
    num_behavioral:  int = 3,
    num_hr:          int = 2,
) -> str:
    """
    Build the complete prompt for generating personalised interview questions.

    Args:
        job_title        : e.g. "Full Stack Developer"
        skills           : detected skills from resume
        experience_level : "fresher" / "junior" / "mid" / "senior"
        resume_summary   : first 600 chars of extracted resume text
        rag_context      : top-K retrieved interview documents (formatted)
        num_technical    : number of technical questions to generate
        num_behavioral   : number of behavioral questions to generate
        num_hr           : number of HR questions to generate

    Returns:
        Complete prompt string ready to send to IBM Granite
    """
    skills_str = ", ".join(skills[:12]) if skills else "general software development"
    total      = num_technical + num_behavioral + num_hr

    return f"""You are an expert technical interviewer at a top tech company.
Generate exactly {total} personalised interview questions for a candidate.

CANDIDATE PROFILE:
- Job Title Applied For: {job_title}
- Experience Level: {experience_level}
- Skills: {skills_str}
- Resume Summary: {resume_summary[:600]}

REFERENCE INTERVIEW CONTENT (use these as inspiration):
{rag_context}

INSTRUCTIONS:
Generate exactly:
- {num_technical} technical questions (test coding/CS knowledge based on their skills)
- {num_behavioral} behavioral questions (STAR method situations)
- {num_hr} HR questions (motivation, goals, culture fit)

Adjust difficulty based on experience level:
- fresher/junior: mostly easy/medium
- mid/senior: mostly medium/hard

Return ONLY a valid JSON array. No extra text before or after.
Each object must have ALL these fields:
- "id": integer starting from 1
- "question": the interview question (clear, specific, relevant to candidate's skills)
- "type": exactly one of "technical", "behavioral", "hr"
- "difficulty": exactly one of "easy", "medium", "hard"
- "topic": specific topic (e.g., "Python", "React", "Problem Solving", "Career Goals")
- "hint": a brief hint for the interviewer about what a good answer covers (1-2 sentences)
- "model_answer": a comprehensive model answer (3-5 sentences)

JSON output:
[
  {{
    "id": 1,
    "question": "...",
    "type": "technical",
    "difficulty": "medium",
    "topic": "...",
    "hint": "...",
    "model_answer": "..."
  }}
]"""


def format_rag_context(retrieved_docs: list[dict], max_docs: int = 8) -> str:
    """
    Format retrieved ChromaDB documents into a readable context block
    for inclusion in the Granite prompt.
    """
    if not retrieved_docs:
        return "No reference content available."

    lines = []
    for i, doc in enumerate(retrieved_docs[:max_docs], 1):
        meta = doc.get("metadata", {})
        q    = meta.get("question", "")
        if q:
            lines.append(f"{i}. [{meta.get('topic','')} | {meta.get('type','')} | {meta.get('difficulty','')}]")
            lines.append(f"   Q: {q[:150]}")

    return "\n".join(lines) if lines else "General interview content."
