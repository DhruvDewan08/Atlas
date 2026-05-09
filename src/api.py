from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from src.pipeline import get_pdf_text, get_text_chunks, create_vector_store
from src.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

app = FastAPI(
    title="Atlas API",
    description="RAG-based document Q&A backend",
    version="1.0.0",
)

# Allow Streamlit (or any frontend) to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary in-memory store — will be replaced with Redis when Celery is added
_vector_store = None


class QueryRequest(BaseModel):
    question: str
    chat_history: List = []


class QueryResponse(BaseModel):
    answer: str


# ------------------------------------------------------------------
# POST /upload
# Accepts one or more PDFs, processes them, stores the vector DB.
# Later: this will fire a Celery task and return a task_id instead.
# ------------------------------------------------------------------
@app.post("/upload", summary="Upload and process PDF documents")
async def upload_documents(files: List[UploadFile] = File(...)):
    global _vector_store
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    raw_text = get_pdf_text(files)
    chunks = get_text_chunks(raw_text)
    _vector_store = create_vector_store(chunks)

    return {
        "message": "Documents processed successfully",
        "chunks_created": len(chunks),
    }


# ------------------------------------------------------------------
# GET /status/{task_id}
# Placeholder for Celery task status — will query Redis result backend.
# ------------------------------------------------------------------
@app.get("/status/{task_id}", summary="Check processing task status")
async def get_status(task_id: str):
    # TODO: query Celery result backend via task_id
    return {"task_id": task_id, "status": "completed"}


# ------------------------------------------------------------------
# POST /query
# Runs RAG chain against the uploaded documents.
# ------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse, summary="Ask a question")
async def query_documents(request: QueryRequest):
    if _vector_store is None:
        raise HTTPException(status_code=400, detail="No documents uploaded yet. Call /upload first.")

    llm = get_llm()
    retriever = _vector_store.as_retriever()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an assistant that answers questions based on the provided documents.
        Use the following context to answer. If you don't know, say so.

        Context: {context}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    chain = (
        RunnablePassthrough.assign(
            context=lambda x: "\n\n".join(d.page_content for d in retriever.invoke(x["input"]))
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke({
        "input": request.question,
        "chat_history": request.chat_history,
    })

    return QueryResponse(answer=answer)