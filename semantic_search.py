
from sentence_transformers import SentenceTransformer
from process_document import process_document

# Load the embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def search_document(question: str, file_path: str) -> None:
    # Read the document and split it into chunks
    chunks = process_document(file_path)

    # Convert document chunks into vectors
    chunk_embeddings = model.encode(
        chunks,
        normalize_embeddings=True
    )

    # Convert the user's question into a vector
    question_embedding = model.encode(
        [question],
        normalize_embeddings=True
    )

    # Compare the question with every chunk
    similarities = chunk_embeddings @ question_embedding[0]

    # Find the chunk with the highest similarity
    best_index = int(similarities.argmax())

    print("\nQuestion:", question)
    print("Most relevant passage:")
    print(chunks[best_index])
    print(f"Similarity score: {similarities[best_index]:.4f}")


if __name__ == "__main__":
    search_document(
        question="How many vacation days do employees get?",
        file_path="data/company_policy.txt"
    )
