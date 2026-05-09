import fitz  # pymupdf
from langchain_chroma import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_ollama import OllamaEmbeddings


def get_pdf_text(pdf_files) -> str:
    """
    Extract raw text from a list of PDF file objects.
    Works with both Streamlit UploadedFile and FastAPI UploadFile (after .read()).
    """
    text = ""
    for pdf in pdf_files:
        doc = fitz.open(stream=pdf.read(), filetype="pdf")
        for page in doc:
            text += page.get_text()
    return text


def get_text_chunks(raw_text: str) -> list[str]:
    """Split raw text into overlapping chunks for embedding."""
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    return text_splitter.split_text(raw_text)


def create_vector_store(text_chunks: list[str]):
    """Embed chunks and store in ChromaDB. Returns the vector store."""
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    vector_store = Chroma.from_texts(texts=text_chunks, embedding=embeddings)
    return vector_store