
from pathlib import Path
import pymupdf


def read_document(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8")

    elif path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as pdf:
            pages = []

            for page in pdf:
                pages.append(page.get_text())

            return "\n".join(pages)

    else:
        raise ValueError("Only TXT and PDF files are supported.")


if __name__ == "__main__":
    content = read_document("data/company_policy.txt")

    print("Extracted document content:")
    print(content)
