import uvicorn
from src.api import app  # noqa: F401 — imported so uvicorn can find it

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
