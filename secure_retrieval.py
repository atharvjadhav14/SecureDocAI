
from database import get_connection


def retrieve_chunks(question: str, tenant_id: int) -> list[str]:
    """
    Retrieve chunks belonging only to the specified tenant.

    This is a basic keyword-search demonstration.
    The tenant ID is supplied directly for now;
    authentication will establish it securely later.
    """
    if not question.strip():
        return []

    with get_connection() as connection:
        chunks = connection.execute(
            """
            SELECT document_chunks.content
            FROM document_chunks
            JOIN documents
                ON document_chunks.document_id = documents.id
            WHERE documents.tenant_id = ?
            """,
            (tenant_id,)
        ).fetchall()

    # Only the authorized tenant's chunks are considered.
    # Replace this basic ranking with semantic retrieval later.
    terms = set(question.lower().split())
    ranked = []

    for row in chunks:
        content = row["content"]
        content_terms = set(content.lower().split())
        score = len(terms & content_terms)

        if score > 0:
            ranked.append((score, content))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [content for _, content in ranked]


if __name__ == "__main__":
    question = "How many vacation days do employees get?"

    # Demo Company currently has tenant ID 1.
    results = retrieve_chunks(question, tenant_id=999)

    print("Question:", question)
    print("Retrieved chunks:", len(results))

    for result in results:
        print("\n", result)
