import streamlit as st
import fitz  # pymupdf
from langchain_chroma import Chroma
from src.llm import get_llm
from langchain_text_splitters import CharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from htmlTemplates import bot_template, user_template, css



def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        # fitz reads directly from bytes — works with Streamlit's file uploader
        doc = fitz.open(stream=pdf.read(), filetype="pdf")
        for page in doc:
            text += page.get_text()
    return text



def get_text_chunks(raw_text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        
    )
    chunks = text_splitter.split_text(raw_text)
    return chunks


def create_vector_store(text_chunks):
    embeddings= OllamaEmbeddings(model="mxbai-embed-large")
    vector_store = Chroma.from_texts(texts=text_chunks,embedding=embeddings)
    return vector_store

def get_conversation_chain(vector_store):
    llm = get_llm()  # uses Ollama or Groq depending on LLM_PROVIDER in .env
    retriever = vector_store.as_retriever()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an assistant that answers questions based on the provided documents.
        Use the following context to answer. If you don't know, say so.

        Context: {context}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        RunnablePassthrough.assign(
            context=lambda x: format_docs(retriever.invoke(x["input"]))
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def handle_userinput(user_question):
    if st.session_state.conversation is None:
        st.warning("Please upload and process a PDF first.")
        return

    response = st.session_state.conversation.invoke({
        "input": user_question,
        "chat_history": st.session_state.chat_history
    })

    # response is now a plain string
    st.session_state.chat_history.extend([
        HumanMessage(content=user_question),
        AIMessage(content=response)
    ])

    # Display full conversation
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Atlas", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
     
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # list of HumanMessage / AIMessage
        
    st.header("Atlas :books:")

    # Main area — Q&A
    user_question = st.text_input("Ask a question about your documents")

    if user_question:
        handle_userinput(user_question)  # Bug 4: removed duplicate Q&A block below that used undefined text_chunks

    # Sidebar — PDF upload
    with st.sidebar:
        st.header("Your documents")
        pdf_docs = st.file_uploader("Upload your PDFs here and click 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                vector_store = create_vector_store(text_chunks)
                st.session_state.conversation = get_conversation_chain(vector_store)
                st.success("You can now ask questions.")  # Bug 5: removed debug st.write(text_chunks)


if __name__ == "__main__":
    main()

