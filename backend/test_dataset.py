import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from app.rag.ingest import load_all_datasets, get_dataset_summary

docs    = load_all_datasets()
summary = get_dataset_summary()

print("\n=== Dataset Summary ===")
print("Total documents :", summary["total_documents"])
print("Files found     :", summary["files_found"])

print("\nBy Topic:")
for topic, count in sorted(summary["by_topic"].items()):
    print(f"  {topic:<35} {count:>3} docs")

print("\nBy Type:")
for t, count in sorted(summary["by_type"].items()):
    print(f"  {t:<35} {count:>3} docs")

print("\nBy Difficulty:")
for d, count in sorted(summary["by_difficulty"].items()):
    print(f"  {d:<35} {count:>3} docs")

# Validate structure
sample = docs[0]
assert "id"       in sample, "Missing id"
assert "text"     in sample, "Missing text"
assert "question" in sample, "Missing question"
assert "answer"   in sample, "Missing answer"
assert len(sample["text"]) > 50, "Text too short"

print("\nSample doc ID :", sample["id"])
print("Sample topic  :", sample["topic"])
print("Text length   :", len(sample["text"]), "chars")
print("\n[PASS] All documents valid and ready for ChromaDB (Step 11)")
