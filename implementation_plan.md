# Atlas — 100% Offline Local RAG PDF QA System

A locally-running **Retrieval-Augmented Generation (RAG)** pipeline that ingests PDF documents, indexes them into a vector database, and answers questions using an LLM. Built as a resume project to demonstrate end-to-end AI/ML microservice engineering skills.

---

## Architecture Overview

```
PDF Documents
     ↓
[1] User Interface         (Streamlit frontend)
     ↓
[2] API Gateway            (FastAPI Backend Server receives upload)
     ↓
[3] Queue                  (FastAPI sends async task to Redis Broker)
     ↓
[4] Background Worker      (Celery pulls task from Redis & monitors via Flower)
     ↓
[5] PDF Ingestion          (PyMuPDF + RecursiveCharacterTextSplitter)
     ↓
[6] Embeddings             (Ollama embed: mxbai-embed-large)
     ↓
[7] Vector Store           (ChromaDB — local, persistent, no cloud)
     ↓
[8] RAG Generation         (FastAPI queries ChromaDB → sends to Ollama llama3.2 → replies to UI)
     ↓
Final Answer
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend UI | **Streamlit** | Beautiful client-facing UI that simply talks to our API. |
| Backend API | **FastAPI** | High-performance Python backend coordinating the application logic. |
| Orchestration Queue | **Redis** | In-memory datastore acting as a lightning-fast local message broker. |
| Background Worker | **Celery** | The asynchronous engine holding the heavy PDF chunking workload. |
| Observability UI | **Flower** | A beautiful local web dashboard to monitor Celery tasks. |
| PDF parsing | **PyMuPDF (fitz)** | Fast, extracts clean text. |
| Chunking | **LangChain** | Sentence-aware, overlap support. |
| Embeddings | **Ollama** | State-of-the-art native embedding model (mxbai-embed-large). |
| Vector DB | **ChromaDB** | Local, persistent, easy API. |
| LLM | **Ollama** | 100% data confidentiality, completely replaces OpenAI (llama3.2). |

---

## Project Structure

```
atlas/
├── data/
│   └── pdfs/              # Uploaded PDFs saved here by FastAPI
├── db/                    # ChromaDB persists here
├── src/
│   ├── __init__.py
│   ├── api.py             # [NEW] FastAPI web server endpoints (/upload, /ask)
│   ├── tasks.py           # Celery worker tasks for background PDF ingestion
│   ├── ingestion.py       # PDF → chunks
│   ├── embeddings.py      # chunks → vectors
│   ├── vector_store.py    # ChromaDB CRUD
│   ├── retriever.py       # semantic search logic
│   ├── llm.py             # LLM prompt + response
│   └── pipeline.py        # Orchestrates full flow
├── app.py                 # Streamlit web UI (Calls API endpoints)
├── cli.py                 # Command-line interface
├── requirements.txt
├── .env.example
└── README.md
```

---

## Proposed Changes

### [NEW] Project Bootstrap
- **requirements.txt**: `fastapi`, `uvicorn`, `celery`, `redis`, `flower`, `streamlit`, `langchain-ollama`, `pymupdf`, `langchain-chroma`.
- **Docker**: `docker-compose.yml` runs Redis and Flower locally.

### [NEW] Source Modules (`src/`)

#### [NEW] src/api.py
- Initializes **FastAPI** server.
- Endpoints:
  - `POST /upload`: Saves file locally, sends job to Celery, returns `task_id`.
  - `GET /task/{task_id}`: Checks Celery task status.
  - `POST /ask`: Receives a prompt, runs retriever, calls LLM, returns answer.

#### [NEW] src/tasks.py
- Defines `@celery.task`.
- Unpacks PDF from `/data` and triggers ingestion.

#### [NEW] src/llm.py & src/embeddings.py
- Now powered entirely by `langchain-ollama`.

### [NEW] Interfaces
- To run this full microservice stack, you will run:
  1. `docker-compose up -d`
  2. `uvicorn src.api:app --reload`
  3. `celery -A src.tasks worker --loglevel=info`
  4. `streamlit run app.py`
