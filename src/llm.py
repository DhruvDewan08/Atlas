import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def get_llm():
    """
    Returns the configured LLM based on LLM_PROVIDER env var.
    - "ollama"  → local Ollama (default for development)
    - "groq"    → Groq API     (use for live demo / deployment)
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("LLM_MODEL", "llama3.2"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    elif provider == "groq":
        # pyrefly: ignore [missing-import]
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY is not set in your .env file.")
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama3-8b-8192"),
            api_key=api_key,
        )

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Use 'ollama' or 'groq'.")


def get_chain():
    """
    Returns a ready-to-use RAG chain: prompt | llm
    Usage:
        chain = get_chain()
        response = chain.invoke({"context": "...", "question": "..."})
    """
    template = """
You are an assistant that answers questions based strictly on the provided documents.
If the answer is not found in the documents, say "I don't know based on the provided documents."

Here is the relevant context retrieved from the documents:
{context}

Here is the question to answer:
{question}
"""
    prompt = ChatPromptTemplate.from_template(template)
    llm = get_llm()
    return prompt | llm
