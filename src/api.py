from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import shutil
from celery.result import AsyncResult
from src.tasks import celery_app, process_document_task
from src.pipeline import get_pdf_text, get_text_chunks, create_vector_store
from src.llm import get_llm
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
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

# Remove the in-memory store
# _vector_store = None

class QueryRequest(BaseModel):
    question: str
    chat_history: List = []

class QueryResponse(BaseModel):
    answer: str

# ------------------------------------------------------------------
# POST /upload
# Accepts one or more PDFs, saves them temporarily, and triggers Celery.
# ------------------------------------------------------------------
@app.post("/upload", summary="Upload and process PDF documents")
async def upload_documents(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Create a temp directory to store files so Celery can read them
    os.makedirs("temp_uploads", exist_ok=True)
    file_paths = []
    
    for file in files:
        file_path = f"temp_uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_paths.append(file_path)

    # Fire and forget: hand the list of file paths to Celery
    task = process_document_task.delay(file_paths)

    return {
        "message": "Documents are being processed in the background",
        "task_id": task.id
    }

# ------------------------------------------------------------------
# GET /status/{task_id}
# Checks Redis to see if the background task is done.
# ------------------------------------------------------------------
@app.get("/status/{task_id}", summary="Check processing task status")
async def get_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.result
        else:
            response["error"] = str(task_result.info)
            
    return response


# ------------------------------------------------------------------
# POST /query
# Runs RAG chain against the uploaded documents.
# ------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse, summary="Ask a question")
async def query_documents(request: QueryRequest):
    # Load the persisted ChromaDB from disk
    if not os.path.exists("./chroma_db"):
        raise HTTPException(status_code=400, detail="No documents have been processed yet.")

    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    vector_store = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    
    llm = get_llm()
    retriever = vector_store.as_retriever()

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