
from pathlib import Path

from database import get_connection, initialize_database
from process_document import process_document


def store_document(file_path: str, tenant_name: str) -> None:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Document not found: {path}")

    # Create the database tables if they don't exist.
    initialize_database()

    # Process the file into text chunks.
    chunks = process_document(str(path))

    with get_connection() as connection:
        # Find or create the tenant.
        connection.execute(
            "INSERT OR IGNORE INTO tenants (name) VALUES (?)",
            (tenant_name,)
        )

        tenant = connection.execute(
            "SELECT id FROM tenants WHERE name = ?",
            (tenant_name,)
        ).fetchone()

        tenant_id = tenant["id"]

        # Register the document.
        cursor = connection.execute(
            """
            INSERT INTO documents (tenant_id, filename)
            VALUES (?, ?)
            """,
            (tenant_id, path.name)
        )

        document_id = cursor.lastrowid

        # Store each chunk with its position.
        connection.executemany(
            """
            INSERT INTO document_chunks
                (document_id, chunk_index, content)
            VALUES (?, ?, ?)
            """,
            [
                (document_id, index, chunk)
                for index, chunk in enumerate(chunks)
            ]
        )

    print(f"Tenant: {tenant_name}")
    print(f"Document: {path.name}")
    print(f"Document ID: {document_id}")
    print(f"Chunks stored: {len(chunks)}")


if __name__ == "__main__":
    store_document(
        file_path="data/company_policy.txt",
        tenant_name="Demo Company"
    )
