"""
prompts/report_gen.py — Final Report Generation Prompts
=========================================================
Prompt for IBM Granite to generate the final interview report summary,
strengths, weaknesses, and personalised learning path.
"""

import json


def build_report_prompt(
    job_title:         str,
    experience_level:  str,
    skills:            list,
    avg_scores:        dict,
    answers_summary:   list,
) -> str:
    """Build the prompt for generating the final interview report."""
    return f"""You are a senior career coach reviewing a mock interview performance.
Generate a comprehensive final report for this candidate.

CANDIDATE:
- Job Title: {job_title}
- Experience Level: {experience_level}
- Skills: {", ".join(skills[:10])}

INTERVIEW SCORES:
- Technical:     {avg_scores.get("technical", 0):.1f}/10
- Communication: {avg_scores.get("communication", 0):.1f}/10
- Behavioral:    {avg_scores.get("behavioral", 0):.1f}/10
- HR:            {avg_scores.get("hr", 0):.1f}/10
- Grammar:       {avg_scores.get("grammar", 0):.1f}/10

ANSWER SUMMARIES:
{json.dumps(answers_summary[:5], indent=2)}

Generate a personalised final report. Return ONLY valid JSON:
{{
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
  "topics_to_improve": ["<topic 1>", "<topic 2>", "<topic 3>"],
  "learning_path": [
    {{"topic": "<topic>", "resource": "<specific course/book>", "priority": "high"}},
    {{"topic": "<topic>", "resource": "<specific course/book>", "priority": "medium"}}
  ],
  "readiness_percentage": <integer 0-100>
}}"""
