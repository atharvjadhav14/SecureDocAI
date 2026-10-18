
from document_reader import read_document
from chunker import split_into_chunks


def process_document(file_path: str) -> list[str]:
    text = read_document(file_path)

    chunks = split_into_chunks(
        text,
        chunk_size=100,
        overlap=20
    )

    return chunks


if __name__ == "__main__":
    file_path = "data/company_policy.txt"

    chunks = process_document(file_path)

    print(f"Total chunks created: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {index}:")
        print(chunk)
