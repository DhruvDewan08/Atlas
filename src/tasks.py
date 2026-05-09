from celery import Celery
import os
from src.pipeline import get_pdf_text, get_text_chunks, create_vector_store
celery_app = Celery(
    "atlas_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task
def process_document_task(file_paths: list[str]):
    """Background task to process PDFs"""
    # 1. Read files from disk (Celery can't receive FastAPI UploadFile directly)
    class DummyFile:
        def __init__(self, path):
            self.path = path
        def read(self):
            with open(self.path, "rb") as f:
                return f.read()
                
    dummy_files = [DummyFile(path) for path in file_paths]
    
    # 2. Run the pipeline
    raw_text = get_pdf_text(dummy_files)
    chunks = get_text_chunks(raw_text)
    create_vector_store(chunks)
    
    # 3. Clean up temporary files
    for path in file_paths:
        os.remove(path)
        
    return {"message": "Success", "chunks": len(chunks)}
