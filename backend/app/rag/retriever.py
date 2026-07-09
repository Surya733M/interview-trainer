"""
rag/retriever.py — Semantic Search & RAG Retrieval
====================================================
Combines embeddings + vector store to answer:
  "Given this resume + job title, what interview content is most relevant?"

Also handles the one-time ingestion of the knowledge base into ChromaDB.
"""

from typing import List, Dict, Optional

from app.rag.embeddings import embedding_model
from app.rag.vector_store import vector_store
from app.rag.ingest import load_all_datasets
from app.utils.logger import logger


def ensure_knowledge_base_populated() -> int:
    """
    Check if ChromaDB is populated; if not, ingest all datasets.
    Called at application startup and before the first retrieval.

    Returns: number of documents in the collection.
    """
    if vector_store.is_populated():
        count = vector_store.count()
        logger.info(f"Knowledge base already populated: {count} documents.")
        return count

    logger.info("Knowledge base is empty. Starting ingestion...")
    return ingest_all_documents()


def ingest_all_documents() -> int:
    """
    Load all datasets, embed them, and store in ChromaDB.
    This is the one-time setup that powers all RAG retrieval.

    Returns: number of documents successfully ingested.
    """
    docs = load_all_datasets()
    if not docs:
        logger.error("No documents found to ingest.")
        return 0

    logger.info(f"Embedding {len(docs)} documents...")

    # Embed in batches to avoid memory issues
    BATCH_SIZE = 32
    ingested   = 0

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i: i + BATCH_SIZE]

        texts = [d["text"] for d in batch]
        try:
            embeddings = embedding_model.embed(texts)
        except Exception as e:
            logger.error(f"Embedding batch {i//BATCH_SIZE} failed: {e}")
            continue

        vector_store.add_documents(
            ids        = [d["id"] for d in batch],
            embeddings = embeddings,
            documents  = [d["text"] for d in batch],
            metadatas  = [
                {
                    "topic":      d["topic"],
                    "type":       d["type"],
                    "difficulty": d["difficulty"],
                    "source":     d["source"],
                    "question":   d["question"][:200],   # truncated for metadata
                }
                for d in batch
            ],
        )
        ingested += len(batch)
        logger.info(f"Ingested {ingested}/{len(docs)} documents...")

    logger.info(f"Knowledge base ingestion complete: {ingested} documents.")
    return ingested


def retrieve_relevant_context(
    resume_text: str,
    job_title:   str,
    skills:      List[str],
    n_results:   int = 10,
    filter_type: Optional[str] = None,
) -> List[Dict]:
    """
    The core RAG retrieval function.

    Given a user's resume context, find the most relevant interview
    documents from the knowledge base.

    Args:
        resume_text : extracted resume text
        job_title   : target job title (e.g. "Full Stack Developer")
        skills      : list of detected skills (e.g. ["Python", "React"])
        n_results   : how many documents to retrieve
        filter_type : optionally filter by type ("technical"/"behavioral"/"hr")

    Returns:
        List of relevant document dicts sorted by relevance (closest first)
    """
    # Ensure the knowledge base is populated before querying
    ensure_knowledge_base_populated()

    # Build a rich query text combining resume context
    # The more context we give, the better the semantic match
    skills_str = ", ".join(skills[:15]) if skills else "software development"
    query_text = (
        f"Job Title: {job_title}\n"
        f"Skills: {skills_str}\n"
        f"Context: {resume_text[:500]}"   # first 500 chars of resume
    )

    # Embed the query
    query_vector = embedding_model.embed_one(query_text)

    # Search ChromaDB
    where = {"type": filter_type} if filter_type else None
    results = vector_store.query(
        query_embedding=query_vector,
        n_results=n_results,
        where=where,
    )

    logger.info(
        f"Retrieved {len(results)} documents for '{job_title}' "
        f"(mode={embedding_model.mode})"
    )
    return results


def retrieve_by_topic(topic: str, n_results: int = 5) -> List[Dict]:
    """Retrieve documents filtered by specific topic."""
    ensure_knowledge_base_populated()
    query_vector = embedding_model.embed_one(f"Interview questions about {topic}")
    return vector_store.query(
        query_embedding=query_vector,
        n_results=n_results,
        where={"topic": topic},
    )
