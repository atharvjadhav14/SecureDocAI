
from sentence_transformers import SentenceTransformer

print("Loading the embedding model...")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

sentences = [
    "Employees receive 18 days of annual paid leave.",
    "Employees must request planned leave at least 3 days in advance.",
    "Emergency leave should be reported to the manager as soon as possible."
]

embeddings = model.encode(sentences)

print("\nEmbedding test successful!")
print("Number of passages:", len(sentences))
print("Embedding shape:", embeddings.shape)
print("\nFirst 10 numbers of the first embedding:")
print(embeddings[0][:10])
