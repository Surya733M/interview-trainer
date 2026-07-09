"""
prompts/evaluation.py — Answer Evaluation Prompts
===================================================
Prompt templates for IBM Granite to evaluate candidate answers
and generate detailed feedback.
"""


def build_evaluation_prompt(
    question:         str,
    question_type:    str,
    answer:           str,
    job_title:        str,
    experience_level: str,
) -> str:
    """
    Build the prompt for evaluating a candidate's answer.

    Returns a prompt that instructs Granite to score the answer
    across 5 dimensions and provide actionable feedback.
    """
    return f"""You are an expert interview evaluator. Evaluate this interview answer.

CONTEXT:
- Job Title: {job_title}
- Experience Level: {experience_level}
- Question Type: {question_type}

QUESTION:
{question}

CANDIDATE'S ANSWER:
{answer}

EVALUATION CRITERIA:
{_get_criteria(question_type)}

SCORING GUIDE:
- 8-10: Excellent — comprehensive, specific, well-structured
- 6-7: Good — covers main points but lacks some depth
- 4-5: Average — partially correct but missing key aspects
- 1-3: Poor — incorrect, too vague, or missing the point

Return ONLY valid JSON with this exact structure:
{{
  "scores": {{
    "technical":      <float 0-10>,
    "grammar":        <float 0-10>,
    "communication":  <float 0-10>,
    "star_method":    <float 0-10>,
    "completeness":   <float 0-10>
  }},
  "overall_score": <float 0-10, weighted average>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<improvement 1>", "<improvement 2>"],
  "model_answer": "<comprehensive ideal answer in 3-5 sentences>",
  "brief_feedback": "<1-2 sentence summary for the candidate>"
}}"""


def _get_criteria(question_type: str) -> str:
    criteria = {
        "technical": (
            "- technical: accuracy and depth of technical knowledge\n"
            "- grammar: clarity and language quality\n"
            "- communication: how well the concept is explained\n"
            "- star_method: not applicable (set to 7.0)\n"
            "- completeness: all aspects of the question addressed"
        ),
        "behavioral": (
            "- technical: relevance to the role (set to 7.0)\n"
            "- grammar: clarity and language quality\n"
            "- communication: storytelling and clarity\n"
            "- star_method: use of Situation, Task, Action, Result structure\n"
            "- completeness: specific example with measurable result"
        ),
        "hr": (
            "- technical: not applicable (set to 7.0)\n"
            "- grammar: clarity and language quality\n"
            "- communication: professionalism and authenticity\n"
            "- star_method: not applicable (set to 7.0)\n"
            "- completeness: addresses the question fully and specifically"
        ),
    }
    return criteria.get(question_type, criteria["hr"])
