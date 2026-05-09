import streamlit as st
import requests
import time

API_URL = "http://localhost:8000"

def main():
    st.set_page_config(page_title="Atlas", page_icon="📚")

    # Initialize state
    if "is_processed" not in st.session_state:
        st.session_state.is_processed = False
     
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [] 
        
    st.title("Atlas 📚")

    # Sidebar — PDF upload
    with st.sidebar:
        st.header("Your documents")
        pdf_docs = st.file_uploader("Upload your PDFs here and click 'Process'", accept_multiple_files=True)
        
        if st.button("Process"):
            if not pdf_docs:
                st.warning("Please upload at least one PDF.")
                return
                
            with st.spinner("Uploading to FastAPI..."):
                files = [("files", (pdf.name, pdf.getvalue(), "application/pdf")) for pdf in pdf_docs]
                
                try:
                    response = requests.post(f"{API_URL}/upload", files=files)
                    if response.status_code == 200:
                        task_id = response.json().get("task_id")
                        status_placeholder = st.empty()
                        
                        while True:
                            status_res = requests.get(f"{API_URL}/status/{task_id}")
                            if status_res.status_code == 200:
                                status_data = status_res.json()
                                status = status_data.get("status")
                                
                                if status == "PENDING":
                                    status_placeholder.info("⏳ Processing documents in the background...")
                                elif status == "SUCCESS":
                                    st.session_state.is_processed = True
                                    status_placeholder.success("✅ Done! You can now ask questions.")
                                    break
                                elif status == "FAILURE":
                                    status_placeholder.error(f"❌ Failed: {status_data.get('error')}")
                                    break
                            else:
                                status_placeholder.error("Error checking status.")
                                break
                                
                            time.sleep(2)
                    else:
                        st.error(f"Failed to start processing: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Failed to connect to backend. Is FastAPI running on port 8000?")

    # Main Chat Interface (ChatGPT style)
    # 1. Display existing chat history
    for role, text in st.session_state.chat_history:
        with st.chat_message("user" if role == "human" else "assistant"):
            st.markdown(text)

    # 2. Chat input fixed at the bottom
    if user_question := st.chat_input("Ask a question about your documents..."):
        if not st.session_state.is_processed:
            st.warning("Please upload and process a PDF first.")
        else:
            # Display user's question immediately
            with st.chat_message("user"):
                st.markdown(user_question)
                
            # Add to history
            st.session_state.chat_history.append(("human", user_question))

            # Fetch AI response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("▌") # Blinking cursor effect
                
                payload = {
                    "question": user_question,
                    "chat_history": st.session_state.chat_history[:-1] # Send history without current question
                }

                try:
                    response = requests.post(f"{API_URL}/query", json=payload)
                    if response.status_code == 200:
                        answer = response.json().get("answer")
                        message_placeholder.markdown(answer)
                        st.session_state.chat_history.append(("ai", answer))
                    else:
                        message_placeholder.error(f"Error from API: {response.text}")
                except requests.exceptions.ConnectionError:
                    message_placeholder.error("Failed to connect to backend. Is FastAPI running on port 8000?")

if __name__ == "__main__":
    main()
