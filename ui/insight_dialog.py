# The click-to-explain modal shared by KPI cards and insight panels.
#
# open_insight(topic) is decorated with @st.dialog, so calling it directly from a
# card/panel button opens the modal. Streamlit keeps the dialog open across the
# follow-up form's reruns automatically, and the native ✕ closes it cleanly — no
# manual open/close flag to go stale.
#
# Persistence: the initial explanation and the follow-up conversation are BOTH
# stored in session_state keyed by `topic`. So closing and re-opening the SAME
# card resumes exactly where you left off, while a DIFFERENT card opens fresh with
# its own explanation and its own chat history.

import streamlit as st

from core.chat import chat, explain


@st.dialog("AI Insight", width="large")
def open_insight(topic: str):
    analysis = st.session_state.get("analysis")
    index = st.session_state.get("rag_index")
    chunks = st.session_state.get("rag_chunks")

    st.markdown(f"#### {topic}")

    # Initial AI explanation — cached per topic so reopening (or a follow-up
    # rerun) never re-hits Gemini for the same card.
    cache = st.session_state.setdefault("insight_cache", {})
    if topic not in cache:
        with st.spinner("Generating insight…"):
            try:
                cache[topic] = explain(topic, analysis)
            except Exception as e:
                cache[topic] = f"_Could not generate insight: {e}_"
    st.markdown(cache[topic])

    st.divider()
    st.markdown("**Ask a follow-up**")

    # Per-topic conversation. setdefault means an existing history is reused on
    # reopen; a brand-new topic starts with an empty list.
    histories = st.session_state.setdefault("insight_histories", {})
    hist = histories.setdefault(topic, [])

    # Message area is created BEFORE the form so it sits above the input, but is
    # filled AFTER we process the submit — so a newly sent message shows this run
    # without calling st.rerun() (which would close the dialog).
    msg_area = st.container()

    with st.form(f"insight_form_{topic}", clear_on_submit=True):
        q = st.text_input("Follow-up", label_visibility="collapsed",
                          placeholder="e.g. which finding drives this the most?")
        send = st.form_submit_button("Send", use_container_width=True)

    if send and q:
        with st.spinner("Thinking…"):
            try:
                answer = chat(q, analysis, hist, index=index, chunks=chunks)
            except Exception as e:
                answer = f"Sorry — I hit an error: {e}"
        hist.append({"role": "user", "content": q})
        hist.append({"role": "assistant", "content": answer})

    with msg_area:
        avatars = {"user": "🧑‍💼", "assistant": "🔍"}
        for m in hist:
            with st.chat_message(m["role"], avatar=avatars.get(m["role"])):
                st.markdown(m["content"])
