import numpy as np
from sentence_transformers import SentenceTransformer

import sqlite3

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from llm_provider import generate_answer

import jwt


from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from auth import (
    create_access_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)
from database import get_connection, initialize_database
from process_document import process_document

import os
import tempfile

app = FastAPI(title="SecureDoc AI API")
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/frontend",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend",
)

@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")
bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)



class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    company_id: int = Field(gt=0)



def normalize_email(email: str) -> str:
    return email.strip().lower()


@app.on_event("startup")
def startup():
    initialize_database()


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    email = normalize_email(str(request.email))
    password_digest = hash_password(request.password)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (?, ?)
                """,
                (email, password_digest),
            )
            user_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return {
        "message": "Account created successfully.",
        "user_id": user_id,
        "email": email,
    }


@app.post("/login")
def login(request: LoginRequest):
    email = normalize_email(str(request.email))

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if user is None or not verify_password(
        request.password, user["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user["id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = get_user_id_from_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"id": user["id"], "email": user["email"]}


@app.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.get("/me/workspaces")
def get_my_workspaces(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                t.id AS company_id,
                t.name AS company_name,
                tm.role AS role
            FROM tenant_memberships AS tm
            JOIN tenants AS t ON t.id = tm.tenant_id
            WHERE tm.user_id = ?
            ORDER BY t.name
            """,
            (user_id,),
        ).fetchall()

    return {
        "workspaces": [
            {
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "role": row["role"],
            }
            for row in rows
        ]
    }


embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


@app.get("/dashboard/summary")
def get_dashboard_summary(
    company_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    with get_connection() as connection:
        # Verify that the user belongs to this workspace and get their role.
        membership = connection.execute(
            """
            SELECT t.id, t.name, tm.role
            FROM tenant_memberships AS tm
            JOIN tenants AS t ON t.id = tm.tenant_id
            WHERE tm.user_id = ? AND tm.tenant_id = ?
            """,
            (user_id, company_id),
        ).fetchone()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this workspace.",
            )

        if membership["role"] != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only company admins can view dashboard statistics.",
            )

        document_count = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM documents
            WHERE tenant_id = ?
            """,
            (company_id,),
        ).fetchone()["total"]

        chunk_count = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE d.tenant_id = ?
            """,
            (company_id,),
        ).fetchone()["total"]

        recent_rows = connection.execute(
            """
            SELECT id, filename, created_at
            FROM documents
            WHERE tenant_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 5
            """,
            (company_id,),
        ).fetchall()

    return {
        "workspace": {
            "company_id": membership["id"],
            "company_name": membership["name"],
            "role": membership["role"],
        },
        "total_documents": document_count,
        "total_chunks": chunk_count,
        "recent_documents": [
            {
                "id": row["id"],
                "filename": row["filename"],
                "created_at": row["created_at"],
            }
            for row in recent_rows
        ],
    }



@app.post("/search")
def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    tenant_id = request.company_id

    with get_connection() as connection:
        # Verify the authenticated user's company membership.
        membership = connection.execute(
            """
            SELECT tenant_id
            FROM tenant_memberships
            WHERE user_id = ? AND tenant_id = ?
            """,
            (current_user["id"], tenant_id),
        ).fetchone()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this company.",
            )

        # Retrieve only this company's document chunks.
        chunks = connection.execute(
            """
            SELECT document_chunks.content, documents.filename
            FROM document_chunks
            JOIN documents
                ON document_chunks.document_id = documents.id
            WHERE documents.tenant_id = ?
            """,
            (tenant_id,),
        ).fetchall()

    if not chunks:
        return {
            "question": question,
            "company_id": tenant_id,
            "answer": (
                "No documents are available in this company's workspace."
            ),
            "sources": [],
        }

    contents = [row["content"] for row in chunks]

    vectors = embedding_model.encode(
        [question] + contents,
        normalize_embeddings=True,
    )

    scores = np.dot(vectors[1:], vectors[0])


    ranked = sorted(
        zip(chunks, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    # Keep only relevant results and remove duplicate sources.
    RELEVANCE_THRESHOLD = 0.30
    top_results = []
    seen_sources = set()

    for row, score in ranked:
        if float(score) < RELEVANCE_THRESHOLD:
            continue

        source_key = (row["filename"], row["content"])

        if source_key in seen_sources:
            continue

        seen_sources.add(source_key)
        top_results.append((row, score))

        if len(top_results) == 3:
            break

    # If no relevant document chunks were found, don't call the AI.
    if not top_results:
        return {
            "question": question,
            "company_id": tenant_id,
            "answer": (
                "I could not find the answer in the authorized documents."
            ),
            "sources": [],
        }


    # Build context only from the authorized company's retrieved chunks.
    context = "\n\n".join(
        f"Source: {row['filename']}\nContent: {row['content']}"
        for row, score in top_results
    )

    try:
        answer = generate_answer(question, context)
    except Exception as exc:
        # Keep provider credentials and internal error details out of the response.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI answer service is temporarily unavailable. Please try again.",
        ) from exc

    sources = [
        {
            "filename": row["filename"],
            "content": row["content"],
            "score": round(float(score), 4),
        }
        for row, score in top_results
    ]

    return {
        "question": question,
        "company_id": tenant_id,
        "answer": answer,
        "sources": sources,
    }


@app.post("/documents/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    company_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    filename = os.path.basename(file.filename or "").strip()
    extension = os.path.splitext(filename)[1].lower()

    if not filename or filename in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid filename is required.",
        )

    if extension not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and TXT files are supported.",
        )

    # Verify workspace membership and admin permissions before processing.
    with get_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM tenant_memberships
            WHERE user_id = ? AND tenant_id = ?
            """,
            (current_user["id"], company_id),
        ).fetchone()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this company.",
        )

    if membership["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can upload documents.",
        )

    max_size = 10 * 1024 * 1024
    temp_path = None

    try:
        # Read no more than 10 MB plus one byte to detect oversized files.
        file_bytes = file.file.read(max_size + 1)

        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )

        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size cannot exceed 10 MB.",
            )

        # Basic content checks; these are useful checks, not full malware scanning.
        if extension == ".pdf" and not file_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The file does not appear to be a valid PDF.",
            )

        if extension == ".txt":
            try:
                file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The TXT file must contain valid UTF-8 text.",
                ) from exc

        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=extension,
            delete=False,
        ) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        chunks = process_document(temp_path)
        clean_chunks = [
            chunk.strip()
            for chunk in chunks
            if isinstance(chunk, str) and chunk.strip()
        ]

        if not clean_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No readable text was found in the document.",
            )

        # The database context manager commits the document and chunks together.
        # If an insert fails, its transaction should be rolled back by get_connection().
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents (tenant_id, filename)
                VALUES (?, ?)
                """,
                (company_id, filename),
            )
            document_id = cursor.lastrowid

            connection.executemany(
                """
                INSERT INTO document_chunks
                    (document_id, chunk_index, content)
                VALUES (?, ?, ?)
                """,
                [
                    (document_id, index, chunk)
                    for index, chunk in enumerate(clean_chunks)
                ],
            )

        return {
            "message": "Document uploaded and processed successfully.",
            "document_id": document_id,
            "company_id": company_id,
            "filename": filename,
            "chunks_stored": len(clean_chunks),
        }

    except HTTPException:
        raise
    except Exception as exc:
        # Avoid returning internal filesystem/database details to the client.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be processed or stored.",
        ) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

        try:
            file.file.close()
        except Exception:
            pass


@app.get("/documents")
def list_documents(
    company_id: int,
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM tenant_memberships
            WHERE user_id = ? AND tenant_id = ?
            """,
            (current_user["id"], company_id),
        ).fetchone()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this company.",
            )

        documents = connection.execute(
            """
            SELECT
                id,
                filename,
                created_at
            FROM documents
            WHERE tenant_id = ?
            ORDER BY id DESC
            """,
            (company_id,),
        ).fetchall()

    return {
        "company_id": company_id,
        "documents": [
            {
                "id": row["id"],
                "filename": row["filename"],
                "created_at": row["created_at"],
            }
            for row in documents
        ],
    }


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    company_id: int,
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM tenant_memberships
            WHERE user_id = ? AND tenant_id = ?
            """,
            (current_user["id"], company_id),
        ).fetchone()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this company.",
            )

        if membership["role"] != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only company admins can delete documents.",
            )

        document = connection.execute(
            """
            SELECT id
            FROM documents
            WHERE id = ? AND tenant_id = ?
            """,
            (document_id, company_id),
        ).fetchone()

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found in this company.",
            )

        connection.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )

        connection.execute(
            "DELETE FROM documents WHERE id = ? AND tenant_id = ?",
            (document_id, company_id),
        )

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
        "company_id": company_id,
    }
