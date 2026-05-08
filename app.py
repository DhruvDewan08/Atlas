import streamlit as st
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_chroma import Chroma
from src.llm import get_llm 
from src.llm import get_chain


def main():
    st.set_page_config(page_title="Atlas", page_icon=":books:")
    st.header("Atlas :books:")

    # Sidebar — PDF upload
    with st.sidebar:
        st.header("Your documents")
        uploaded_file = st.file_uploader("Upload your PDFs here and click 'Process'")
        st.button("Process")

    # Main area — Q&A
    user_question = st.text_input("Ask a question about your documents")

    if user_question:
        chain = get_chain()
        # TODO: replace [] with actual retrieved docs from ChromaDB
        response = chain.invoke({"context": [], "question": user_question})
        st.write(response)


if __name__ == "__main__":
    main()