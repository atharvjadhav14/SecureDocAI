# SecureDoc AI — Permission-Aware Multi-Tenant RAG

SecureDoc AI is an AI-powered document assistant designed to help users retrieve answers from company documents while enforcing tenant-based access control.

The project combines document processing, semantic search, authentication, and a large language model to provide context-grounded answers from authorized documents.

## Key Features

- **Authentication:** User registration and login using password hashing and JWT-based authentication.
- **Multi-Tenant Access Control:** Workspace membership and role checks to help isolate company data.
- **Document Processing:** Extracts text from supported PDF and TXT documents and splits it into chunks.
- **Semantic Search:** Uses sentence embeddings and similarity ranking to retrieve relevant document content.
- **Context-Grounded Answers:** Uses a Groq-hosted language model to generate answers from retrieved document context.
- **Document Management:** Supports document upload, listing, and deletion subject to authorization.
- **Web Interface:** Provides a frontend for authentication, document management, and AI-assisted search.

## Technology Stack

| Component           | Technologies                           |
| ------------------- | -------------------------------------- |
| Backend             | Python, FastAPI                        |
| Frontend            | HTML, CSS, JavaScript                  |
| Database            | SQLite                                 |
| Authentication      | JWT, Argon2 password hashing           |
| Embeddings          | Sentence Transformers                  |
| Similarity Search   | FAISS and vector similarity techniques |
| Language Model      | Groq API                               |
| Document Processing | PyMuPDF                                |

## Architecture

1. A user authenticates and accesses an authorized workspace.
2. Documents are uploaded and their text is extracted.
3. Extracted text is divided into chunks and stored with document and tenant information.
4. A user's question is converted into an embedding.
5. Relevant chunks are retrieved from the authorized tenant's documents.
6. The retrieved context is sent to the language model.
7. The answer is returned to the user.

## Project Structure

```text
SecureDocAI/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── auth.py
├── chunker.py
├── database.py
├── document_reader.py
├── embeddings.py
├── faiss_search.py
├── llm_provider.py
├── main.py
├── process_document.py
├── secure_retrieval.py
├── secure_semantic_search.py
├── semantic_search.py
├── store_document.py
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.12 recommended
- Git
- A Groq API key

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/atharvjadhav14/SecureDocAI.git
cd SecureDocAI
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Set your Groq API key and JWT secret in PowerShell. Use your own secret values and never commit them to Git.

```powershell
$env:GROQ_API_KEY = "YOUR_GROQ_API_KEY"
$env:SECUREDOC_JWT_SECRET = "YOUR_LONG_RANDOM_SECRET"
```

### 5. Run the application

```powershell
python -m uvicorn main:app --reload
```

Open the API documentation at:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The frontend is located in the `frontend/` directory. Follow the project's configured frontend-serving approach when opening the web interface.

## Security Considerations

- Passwords should be stored as secure hashes, not plain text.
- API keys and JWT secrets must be provided through environment variables.
- Authenticated endpoints should verify user identity and workspace membership.
- Document retrieval must enforce tenant-level access restrictions.
- Production deployments require secure secret management, HTTPS, and persistent database storage.

## Current Limitations

- Answer quality depends on the relevance and completeness of retrieved document chunks.
- SQLite requires a suitable persistence strategy when deployed to hosting environments with ephemeral filesystems.
- Production deployment, monitoring, and broader security testing should be completed before real organizational use.

## Future Improvements

- More robust document relevance evaluation and retrieval tuning.
- Improved document ingestion and processing.
- Workspace invitations and user-management workflows.
- Production-ready database hosting and deployment.
- Expanded automated security and retrieval tests.

## Author

Developed as an AI/ML project exploring retrieval-augmented generation, document intelligence, and multi-tenant access control.
