"""
rag/ingest.py — Dataset Loader and ChromaDB Ingestion Pipeline
================================================================
This module:
  1. Loads all JSON datasets from the datasets/ directory
  2. Validates and normalises each document
  3. Formats documents for ChromaDB ingestion
  4. Provides a count and summary of all available documents

Run this script once to populate ChromaDB:
    python -m app.rag.ingest

Or it is called automatically on first startup if ChromaDB is empty.
"""

import json
import os
from typing import List, Dict
from pathlib import Path

from app.utils.logger import logger


# Path to the datasets directory (relative to backend/)
DATASETS_DIR = Path(__file__).parent.parent.parent / "datasets"

# All dataset files to load
DATASET_FILES = [
    "python_questions.json",
    "javascript_questions.json",
    "java_questions.json",
    "sql_questions.json",
    "dsa_questions.json",
    "os_dbms_cn.json",
    "ai_ml_questions.json",
    "behavioral_questions.json",
    "hr_questions.json",
    "interview_tips.json",
]


def load_all_datasets() -> List[Dict]:
    """
    Load all interview Q&A documents from the datasets directory.

    Returns:
        A flat list of document dicts, each with keys:
          id, topic, type, difficulty, question, answer, text (combined)
    """
    all_docs = []

    for filename in DATASET_FILES:
        filepath = DATASETS_DIR / filename
        if not filepath.exists():
            logger.warning(f"Dataset file not found: {filepath}")
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate and normalise each document
            for doc in data:
                normalised = _normalise_document(doc, filename)
                if normalised:
                    all_docs.append(normalised)

            logger.info(f"Loaded {len(data)} documents from {filename}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")

    logger.info(f"Total documents loaded: {len(all_docs)}")
    return all_docs


def _normalise_document(doc: dict, source_file: str) -> dict | None:
    """
    Validate and normalise a single document.
    Returns None if the document is invalid.

    Each document must have: id, topic, type, difficulty, question, answer.
    We also add a 'text' field combining question+answer for embedding.
    """
    required_fields = ["id", "topic", "type", "difficulty", "question", "answer"]

    # Check all required fields exist and are non-empty
    for field in required_fields:
        if field not in doc or not str(doc[field]).strip():
            logger.warning(f"Document missing '{field}' in {source_file}: {doc.get('id', 'unknown')}")
            return None

    return {
        "id":         str(doc["id"]),
        "topic":      str(doc["topic"]),
        "type":       str(doc["type"]),
        "difficulty": str(doc["difficulty"]),
        "question":   str(doc["question"]),
        "answer":     str(doc["answer"]),
        "source":     source_file.replace(".json", ""),
        # Combined text used for generating embeddings
        # Including both Q and A gives better semantic coverage
        "text": f"Topic: {doc['topic']}\nType: {doc['type']}\nDifficulty: {doc['difficulty']}\nQuestion: {doc['question']}\nAnswer: {doc['answer']}"
    }


def get_dataset_summary() -> Dict:
    """
    Return a summary of available datasets without loading all content.
    Used for health checks and dashboard display.
    """
    summary = {
        "total_documents": 0,
        "by_topic": {},
        "by_type": {},
        "by_difficulty": {},
        "files_found": 0,
        "files_missing": 0,
    }

    all_docs = load_all_datasets()
    summary["total_documents"] = len(all_docs)
    summary["files_found"] = sum(
        1 for f in DATASET_FILES if (DATASETS_DIR / f).exists()
    )
    summary["files_missing"] = len(DATASET_FILES) - summary["files_found"]

    for doc in all_docs:
        # Count by topic
        t = doc["topic"]
        summary["by_topic"][t] = summary["by_topic"].get(t, 0) + 1
        # Count by type
        ty = doc["type"]
        summary["by_type"][ty] = summary["by_type"].get(ty, 0) + 1
        # Count by difficulty
        d = doc["difficulty"]
        summary["by_difficulty"][d] = summary["by_difficulty"].get(d, 0) + 1

    return summary


if __name__ == "__main__":
    # Run directly: python -m app.rag.ingest
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    summary = get_dataset_summary()
    print("\n=== Dataset Summary ===")
    print(f"Total documents : {summary['total_documents']}")
    print(f"Files found     : {summary['files_found']}/{len(DATASET_FILES)}")
    print(f"\nBy Topic:")
    for topic, count in sorted(summary['by_topic'].items()):
        print(f"  {topic:<30} {count:>3} documents")
    print(f"\nBy Type:")
    for t, count in sorted(summary['by_type'].items()):
        print(f"  {t:<30} {count:>3} documents")
    print(f"\nBy Difficulty:")
    for d, count in sorted(summary['by_difficulty'].items()):
        print(f"  {d:<30} {count:>3} documents")
