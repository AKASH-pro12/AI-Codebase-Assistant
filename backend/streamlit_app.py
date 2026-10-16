import requests
import streamlit as st


FASTAPI_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="AI Codebase Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)


if "messages" not in st.session_state:
    st.session_state.messages = []

if "codebase_processed" not in st.session_state:
    st.session_state.codebase_processed = False

if "codebase_name" not in st.session_state:
    st.session_state.codebase_name = None

if "previous_sources" not in st.session_state:
    st.session_state.previous_sources = []


st.markdown(
    """
    <style>

    .main-title {
        font-size: 32px;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .subtitle {
        font-size: 16px;
        color: #666666;
        margin-bottom: 30px;
    }

    .status-card {
        padding: 14px 18px;
        border-radius: 8px;
        border: 1px solid #dddddd;
        background-color: #fafafa;
        margin-bottom: 20px;
    }

    .source-file {
        font-size: 13px;
        margin-bottom: 6px;
        color: #555555;
    }

    </style>
    """,
    unsafe_allow_html=True
)


st.markdown(
    '<div class="main-title">AI Codebase Assistant</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Understand, explore, and query your software codebase using natural language.'
    '</div>',
    unsafe_allow_html=True
)


# Sidebar

with st.sidebar:

    st.header("Codebase")

    uploaded_file = st.file_uploader(
        "Upload repository",
        type=["zip"],
        help="Upload your project as a ZIP file."
    )

    if uploaded_file:

        st.write(
            f"Selected file: {uploaded_file.name}"
        )

        if st.button(
            "Process Codebase",
            use_container_width=True
        ):

            with st.spinner(
                "Processing codebase..."
            ):

                try:

                    response = requests.post(
                        f"{FASTAPI_URL}/codebase/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                "application/zip"
                            )
                        },
                        timeout=300
                    )

                    if response.status_code == 200:

                        result = response.json()

                        st.session_state.codebase_processed = True
                        st.session_state.codebase_name = uploaded_file.name

                        st.session_state.messages = []
                        st.session_state.previous_sources = []

                        st.success(
                            "Codebase processed successfully."
                        )

                        st.write(
                            f"Files: {result['total_files']}"
                        )

                        st.write(
                            f"Chunks: {result['total_chunks']}"
                        )

                    else:

                        st.error(
                            f"Processing failed: {response.text}"
                        )

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Unable to connect to the FastAPI server. "
                        "Make sure the backend is running."
                    )

                except requests.exceptions.Timeout:

                    st.error(
                        "Codebase processing timed out. "
                        "Please try again."
                    )

                except requests.exceptions.RequestException as error:

                    st.error(
                        f"Request failed: {error}"
                    )

    st.divider()

    if st.session_state.codebase_processed:

        st.success("Codebase ready")

        if st.session_state.codebase_name:

            st.caption(
                st.session_state.codebase_name
            )

    else:

        st.info(
            "Upload and process a codebase to start asking questions."
        )

    st.divider()

    if st.button(
        "Clear Conversation",
        use_container_width=True
    ):

        st.session_state.messages = []
        st.session_state.previous_sources = []

        st.rerun()


st.subheader("Conversation")


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )

        if (
            message["role"] == "assistant"
            and message.get("sources")
        ):

            unique_sources = list(
                dict.fromkeys(
                    source["file_path"]
                    for source in message["sources"]
                    if source.get("file_path")
                )
            )

            with st.expander("Sources"):

                for file_path in unique_sources:

                    st.markdown(
                        f'<div class="source-file">'
                        f'{file_path}'
                        f'</div>',
                        unsafe_allow_html=True
                    )


question = st.chat_input(
    "Ask a question about your codebase..."
)


if question:

    chat_history = st.session_state.messages.copy()

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)

    with st.chat_message("assistant"):

        if not st.session_state.codebase_processed:

            answer = (
                "Please upload and process a codebase "
                "before asking questions."
            )

            st.warning(answer)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": []
                }
            )

        else:

            with st.spinner(
                "Analyzing the codebase..."
            ):

                try:

                    response = requests.post(
                        f"{FASTAPI_URL}/codebase/search",
                        json={
                            "query": question,
                            "limit": 5,
                            "chat_history": chat_history,
                            "previous_sources": (
                                st.session_state.previous_sources
                            )
                        },
                        timeout=120
                    )

                    if response.status_code == 200:

                        result = response.json()

                        answer = result.get(
                            "answer",
                            "No answer was generated."
                        )

                        sources = result.get(
                            "sources",
                            []
                        )

                        st.session_state.previous_sources = list(
                            dict.fromkeys(
                                source["file_path"]
                                for source in sources
                                if source.get("file_path")
                            )
                        )

                        st.markdown(answer)

                        if sources:

                            unique_sources = list(
                                dict.fromkeys(
                                    source["file_path"]
                                    for source in sources
                                    if source.get("file_path")
                                )
                            )

                            with st.expander("Sources"):

                                for file_path in unique_sources:

                                    st.markdown(
                                        f'<div class="source-file">'
                                        f'{file_path}'
                                        f'</div>',
                                        unsafe_allow_html=True
                                    )

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "sources": sources
                            }
                        )

                    else:

                        answer = (
                            f"Search request failed: "
                            f"{response.text}"
                        )

                        st.error(answer)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "sources": []
                            }
                        )

                except requests.exceptions.ConnectionError:

                    answer = (
                        "Unable to connect to the FastAPI server. "
                        "Make sure the backend is running."
                    )

                    st.error(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": []
                        }
                    )

                except requests.exceptions.Timeout:

                    answer = (
                        "The request took too long to complete. "
                        "Please try again."
                    )

                    st.error(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": []
                        }
                    )

                except requests.exceptions.RequestException as error:

                    answer = (
                        f"An error occurred while "
                        f"processing the request: {error}"
                    )

                    st.error(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": []
                        }
                    )