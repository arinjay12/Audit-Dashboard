# The persistent chat assistant, docked at the bottom of the dashboard.
#
# It lives inside an st.expander so it can be collapsed/expanded by clicking the
# header — and crucially, an expander toggles CLIENT-SIDE with a smooth animation
# and NO full rerun (unlike a button-driven minimize, which reloads the page).
#
# The one catch with expanders is that st.chat_input renders nothing inside them,
# so the input is a small st.form (text box + Send) instead. Sending a message
# still reruns — that's unavoidable, it has to call Gemini — but opening/closing
# the chat no longer does. The conversation lives in session_state, so it
# survives both the collapse and the reruns.
#
# `document` scopes the chat to a single file (used by Page 3): answers are
# limited to that document and it keeps its OWN conversation history, separate
# from the global Page 2 chat and from other documents.

import streamlit as st

from core.chat import chat


def render_chat_panel(document: str = None):
    if document:
        title = f"💬 Assistant — {document}"
    else:
        title = "💬 Audit Assistant"

    with st.expander(title, expanded=True):
        analysis = st.session_state.get("analysis")
        if analysis is None:
            st.info("Upload documents first to enable chat.")
            return

        index = st.session_state.get("rag_index")
        chunks = st.session_state.get("rag_chunks")

        # Pick the conversation + widget keys. A document-scoped chat gets its own
        # history bucket keyed by filename; the global chat uses chat_history.
        if document:
            st.caption(f"Answers are scoped to **{document}** only.")
            histories = st.session_state.setdefault("doc_chat_histories", {})
            history = histories.setdefault(document, [])
            form_key = f"chat_form::{document}"
        else:
            st.caption("Ask about findings, vendors, figures, or specific pages of the documents.")
            history = st.session_state.chat_history
            form_key = "chat_form"

        # Existing conversation.
        avatars = {"user": "🧑‍💼", "assistant": "🔍"}
        for msg in history:
            with st.chat_message(msg["role"], avatar=avatars.get(msg["role"])):
                st.markdown(msg["content"])

        # Input row: a form so the page only reruns on Send, not on each keystroke.
        with st.form(form_key, clear_on_submit=True):
            cols = st.columns([6, 1])
            user_input = cols[0].text_input(
                "Message", label_visibility="collapsed",
                placeholder="Ask a question about the audit…",
            )
            send = cols[1].form_submit_button("Send", use_container_width=True)

        if send and user_input:
            with st.spinner("Thinking…"):
                try:
                    answer = chat(user_input, analysis, history,
                                  index=index, chunks=chunks, document=document)
                except Exception as e:
                    answer = f"Sorry — I hit an error answering that: {e}"
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": answer})
            st.rerun()
