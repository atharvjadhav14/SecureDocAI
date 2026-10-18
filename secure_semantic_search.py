
import numpy as np
from sentence_transformers import SentenceTransformer

from database import get_connection


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Initial threshold; we will evaluate and tune this later.
MIN_SIMILARITY = 0.40


def search_authorized_documents(
    question: str,
    tenant_id: int,
    top_k: int = 3
) -> list[dict]:
    if not question.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    # Retrieve only chunks belonging to the requested tenant.
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                document_chunks.id AS chunk_id,
                document_chunks.content,
                documents.filename
            FROM document_chunks
            JOIN documents
                ON document_chunks.document_id = documents.id
            WHERE documents.tenant_id = ?
            """,
            (tenant_id,)
        ).fetchall()

    if not rows:
        return []

    chunks = [row["content"] for row in rows]

    # Embed authorized document chunks.
    chunk_vectors = model.encode(
        chunks,
        normalize_embeddings=True
    )
    chunk_vectors = np.asarray(chunk_vectors, dtype="float32")

    # Embed the user's question.
    question_vector = model.encode(
        [question],
        normalize_embeddings=True
    )
    question_vector = np.asarray(question_vector, dtype="float32")

    # Calculate cosine similarity.
    scores = chunk_vectors @ question_vector[0]

    # Rank chunks from highest to lowest similarity.
    best_indices = np.argsort(scores)[::-1]

    results = []

    for index in best_indices:
        score = float(scores[int(index)])

        # Exclude weak matches.
        if score < MIN_SIMILARITY:
            continue

        results.append({
            "chunk_id": rows[int(index)]["chunk_id"],
            "filename": rows[int(index)]["filename"],
            "content": chunks[int(index)],
            "similarity": score
        })

        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    question = "How many vacation days do employees get?"

    results = search_authorized_documents(
        question=question,
        tenant_id=1,
        top_k=3
    )

    print("Question:", question)
    print("Results found:", len(results))

    for result in results:
        print("\nFile:", result["filename"])
        print("Passage:", result["content"])
        print(f"Similarity: {result['similarity']:.4f}")

    print("\nTesting an unknown tenant...")
    other_results = search_authorized_documents(
        question=question,
        tenant_id=999,
        top_k=3
    )
    print("Results for tenant 999:", len(other_results))
