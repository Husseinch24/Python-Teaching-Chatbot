# 3_chatbot.py - FINAL HYBRID Ollama + Gemini RAG Chatbot

import os
import json
import re 

from datetime import datetime

from dotenv import load_dotenv
import streamlit as st

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# --------------------------------------------------------------------------------
# Load environment
# --------------------------------------------------------------------------------
load_dotenv()

# --------------------------------------------------------------------------------
# Initialize embeddings + Chroma
# --------------------------------------------------------------------------------
embeddings = OllamaEmbeddings(model=os.getenv("EMBEDDING_MODEL"))

vector_store = Chroma(
    collection_name=os.getenv("COLLECTION_NAME"),
    embedding_function=embeddings,
    persist_directory=os.getenv("DATABASE_LOCATION"),
)

# --------------------------------------------------------------------------------
# Small-talk detector
# --------------------------------------------------------------------------------
def is_small_talk(query: str):
    small_talk_keywords = [
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "how are you", "what's up", "who are you"
    ]
    q = query.lower().strip()
    return any(kw in q for kw in small_talk_keywords)

# --------------------------------------------------------------------------------
# Retrieval + confidence
# --------------------------------------------------------------------------------
def retrieve_documents(query: str, k: int = 6):
    try:
        results = vector_store.similarity_search_with_score(query, k=k)
    except Exception:
        docs = vector_store.similarity_search(query, k=k)
        results = [(doc, 0.0) for doc in docs]

    if not results:
        return [], 0

    keywords = [w.lower() for w in query.split() if len(w) > 3]
    scored = []

    for doc, score in results:
        text_lower = doc.page_content.lower()
        kw_matches = sum(1 for kw in keywords if kw in text_lower)
        inv_score = 1.0 - float(score) if score is not None else 0.0
        hybrid_score = inv_score + kw_matches * 0.5
        scored.append((doc, hybrid_score, kw_matches))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_docs = [s[0] for s in scored[:k]]

    avg_kw = sum(s[2] for s in scored[:k]) / max(len(scored[:k]), 1)
    confidence = 40 + int(avg_kw * 15)
    confidence = max(0, min(100, confidence))

    return top_docs, confidence


def build_context(docs):
    blocks = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "N/A")
        title = doc.metadata.get("title", "")
        blocks.append(
            f"[{i}] Source: {source}\nTitle: {title}\nContent:\n{doc.page_content}"
        )
    return "\n\n".join(blocks)


def format_chat_history(messages):
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            lines.append(f"User: {m.content}")
        elif isinstance(m, AIMessage):
            lines.append(f"Assistant: {m.content}")
    return "\n".join(lines)

# --------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------
def log_interaction(question, answer, docs, confidence, model_name):
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"chatlog_{datetime.now().strftime('%Y%m%d')}.jsonl")

    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "sources": [
            {"source": d.metadata.get("source", "N/A"), "title": d.metadata.get("title", "")}
            for d in docs
        ],
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# --------------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid RAG Chatbot", page_icon="🦜")
st.title("🦜 Hybrid RAG Chatbot (Ollama + Gemini)")

with st.sidebar:
    st.header("Settings")

    model_choice = st.radio(
        "LLM Provider",
        ["Local Ollama", "Cloud Gemini"],
        index=0
    )

    answer_mode = st.radio(
        "Answering mode",
        ["Study (detailed)", "Quick (concise)", "Exam (step-by-step)"],
        index=0
    )

    audience_level = st.radio(
        "Audience level",
        ["Simple", "Normal", "Advanced"],
        index=1
    )

    show_sources = st.checkbox("Show retrieved passages", value=False)

    st.markdown("---")
    if st.button("Reset Chat Session"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.write("Hybrid Local + Cloud RAG System")

# --------------------------------------------------------------------------------
# Dynamic LLM Selection
# --------------------------------------------------------------------------------
if model_choice == "Local Ollama":
    llm = init_chat_model(
        os.getenv("CHAT_MODEL"),
        model_provider=os.getenv("MODEL_PROVIDER"),
        temperature=0
    )
    active_model_name = "ollama"
else:
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-flash-latest",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    )
    active_model_name = "gemini"

# --------------------------------------------------------------------------------
# Strict Prompt Rules
# --------------------------------------------------------------------------------
MODE_RULES = {
    "Study (detailed)": """
Provide an in-depth explanation of at least 3 full paragraphs.
Include definitions, background, and an example.
""",
    "Quick (concise)": """
Provide a summary in exactly 3 bullet points.
Each bullet must be no longer than one sentence.
""",
    "Exam (step-by-step)": """
Provide a step-by-step structured answer.
Use numbered steps.
Explain the logic clearly as if answering in an exam.
"""
}

LEVEL_RULES = {
    "Simple": """
Use only basic vocabulary.
No jargon.
Explain as if to a high-school student.
""",
    "Normal": """
Use standard undergraduate-level technical terms.
Balanced explanation.
""",
    "Advanced": """
Use formal academic language.
Assume knowledge of AI, ML, and NLP concepts.
Use precise terminology.
"""
}

# --------------------------------------------------------------------------------
# Chat Memory
# --------------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)
            st.caption(f"Model used: {active_model_name}")

user_question = st.chat_input("Ask something about Python, LangChain, Ollama, or Chroma...")

# --------------------------------------------------------------------------------
# Main Chat Logic
# --------------------------------------------------------------------------------
if user_question:

    with st.chat_message("user"):
        st.markdown(user_question)
    st.session_state.messages.append(HumanMessage(user_question))

    # Small talk bypass
    if is_small_talk(user_question):
        greeting = "Hello! I am your Hybrid RAG assistant. Ask me about Python, LangChain, Ollama, or this system."
        with st.chat_message("assistant"):
            st.markdown(greeting)
            st.caption(f"Model used: {active_model_name}")
        st.session_state.messages.append(AIMessage(greeting))
        st.stop()

    # Retrieval
    docs, confidence = retrieve_documents(user_question, k=6)
    context = build_context(docs)
    history_text = format_chat_history(st.session_state.messages[:-1])

    # Hard hallucination cutoff
    if confidence < 30:
        refusal = "I don't know based on the provided documents."
        with st.chat_message("assistant"):
            st.markdown(refusal)
            st.caption(f"Model used: {active_model_name}")

        st.session_state.messages.append(AIMessage(refusal))
        log_interaction(user_question, refusal, docs, confidence, active_model_name)
        st.stop()

    if show_sources:
        st.subheader("Retrieved Context")
        st.text(context)

    system_instructions = f"""
You are a strict Retrieval-Augmented Generation assistant.

RULES:
1. Answer ONLY from the provided context.
2. If the answer is not in the context, say: "I don't know based on the provided documents."
3. Follow MODE rules:
{MODE_RULES[answer_mode]}
4. Follow AUDIENCE rules:
{LEVEL_RULES[audience_level]}
5. Never use external knowledge.
6. Do NOT include any citation numbers like [1], [2], [3] inside the answer.

FORMAT:
Answer:
<text>


"""


    user_prompt = f"""
CONTEXT:
{context}

CHAT HISTORY:
{history_text}

QUESTION:
{user_question}
"""

    conversation = [
        SystemMessage(system_instructions),
        *st.session_state.messages[:-1],
        HumanMessage(user_prompt),
    ]

    response = llm.invoke(conversation)
    ai_text = response.content
    ai_text = re.sub(r"\[\d+\]", "", ai_text)  # removes [1], [2], [15], etc.


    with st.chat_message("assistant"):
        st.markdown(ai_text)
        st.caption(f"Model used: {active_model_name}")

    st.session_state.messages.append(AIMessage(ai_text))

    log_interaction(
        user_question,
        ai_text,
        docs,
        confidence,
        active_model_name
    )
