
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from process_document import process_document

# 1. Load the embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# 2. Read and split the company policy
chunks = process_document("data/company_policy.txt")

# 3. Convert the chunks into numerical vectors
embeddings = model.encode(
    chunks,
    normalize_embeddings=True
)

# FAISS expects a NumPy array of 32-bit floats
embeddings = np.asarray(embeddings, dtype="float32")

# 4. Create a FAISS index for 384-dimensional vectors
index = faiss.IndexFlatIP(embeddings.shape[1])

# 5. Add document vectors to the index
index.add(embeddings)

# 6. Convert a question into a vector
question = "How many vacation days do employees get?"

question_embedding = model.encode(
    [question],
    normalize_embeddings=True
)

question_embedding = np.asarray(
    question_embedding,
    dtype="float32"
)

# 7. Search for the most relevant chunk
scores, indices = index.search(question_embedding, k=1)

best_index = int(indices[0][0])

print("Question:", question)
print("\nMost relevant passage:")
print(chunks[best_index])
print(f"\nSimilarity score: {scores[0][0]:.4f}")
