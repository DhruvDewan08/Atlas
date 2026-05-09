from celery import Celery
import os

celery_app = Celery(
    "atlas",
    broker=os.getenv("CELERY_BROKER_URL"),      # Redis receives the job
    backend=os.getenv("CELERY_RESULT_BACKEND")  # Redis stores the result
)

@celery_app.task
def process_pdf_task(file_bytes: bytes, filename: str):
    # this runs in the background
    from src.pipeline import get_pdf_text, get_text_chunks, create_vector_store
    
    raw_text = get_pdf_text(file_bytes)
    chunks = get_text_chunks(raw_text)
    create_vector_store(chunks)
    
    return {"status": "done", "filename": filename}