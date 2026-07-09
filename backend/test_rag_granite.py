import os
os.makedirs('./uploads', exist_ok=True)
os.makedirs('./reports', exist_ok=True)
os.makedirs('./logs', exist_ok=True)

from app.rag.embeddings   import embedding_model
from app.rag.vector_store import vector_store
from app.rag.retriever    import ensure_knowledge_base_populated, retrieve_relevant_context
from app.rag.ingest       import load_all_datasets
from app.services.granite_service import granite
from app.services.report_service  import generate_report
from app.services.pdf_service     import generate_pdf_report
from app.prompts.question_gen     import build_question_generation_prompt, format_rag_context
from app.prompts.evaluation       import build_evaluation_prompt
from app.prompts.report_gen       import build_report_prompt
print("[PASS] All modules imported")

# Test embedding
vec = embedding_model.embed_one("What is Python?")
assert len(vec) > 0
print(f"[PASS] Embedding: mode={embedding_model.mode}, dims={len(vec)}")

# Test RAG ingestion
count = ensure_knowledge_base_populated()
assert count > 0
print(f"[PASS] ChromaDB: {count} documents")

# Test semantic retrieval
results = retrieve_relevant_context(
    resume_text="Python developer with React and SQL",
    job_title="Full Stack Developer",
    skills=["Python","React","SQL"],
    n_results=5,
)
assert len(results) > 0
top = results[0]
print(f"[PASS] Semantic search: {len(results)} results")
print(f"       Top: {top['metadata']['topic']} | {top['metadata']['question'][:60]}")

# Test Granite check
print(f"[PASS] Granite: available={granite.is_available}")

# Test prompts
prompt = build_question_generation_prompt(
    job_title="Python Developer",
    skills=["Python","FastAPI","SQL"],
    experience_level="junior",
    resume_summary="Python dev, 1 year exp",
    rag_context=format_rag_context(results),
)
assert "Python Developer" in prompt
print(f"[PASS] Question prompt: {len(prompt)} chars")

eval_p = build_evaluation_prompt("What is a decorator?","technical","A wrapper function.","Python Dev","junior")
assert "decorator" in eval_p.lower()
print(f"[PASS] Evaluation prompt: {len(eval_p)} chars")

print()
print("====================================================")
print(" Steps 11-14 Integration: ALL PASSED")
print("====================================================")
print(f" ChromaDB   : {count} documents ready")
print(f" Embeddings : {embedding_model.mode} mode")
print(f" Granite    : {'REAL AI' if granite.is_available else 'Fallback mode (set .env creds for real AI)'}")
