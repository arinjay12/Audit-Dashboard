"""
RAG (Retrieval Augmented Generation) support for the chat pipeline.

After documents are extracted, call build_index() once to chunk and embed them.
On each chat query, call query() to retrieve the most relevant chunks.

The embedding model (all-MiniLM-L6-v2, ~80MB) downloads automatically on first use.
"""

import re
import numpy as np

from core.schema import ParsedDoc

CHUNK_SIZE = 400    # words per chunk
CHUNK_OVERLAP = 50  # words of overlap between consecutive chunks

_model = None


def _get_model():
    """
    Load the embedding model on first use. The sentence_transformers/torch
    import chain takes tens of seconds cold, so it's deferred here rather than
    paid at module import — the app's first page renders immediately, and the
    cost lands inside the upload pipeline where a progress panel is showing.
    The loaded model is cached for the life of the server process.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer   # deferred heavy import
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _chunk_text(text: str, filename: str) -> list[dict]:
    """
    Splits text into overlapping chunks. Tracks the [Page N] markers that
    extract.py injects so every chunk knows which page(s) it came from — this
    lets queries like "what's on page 7" retrieve the right chunk by page.

    extract.py writes the marker WITH a space ("[Page 7]"). Splitting on
    whitespace would break it into two tokens, so we first collapse the marker
    into a single token ("[Page_7]") before splitting.
    """
    text = re.sub(r"\[Page\s+(\d+)\]", r"[Page_\1]", text)
    words = text.split()

    # Walk every word, tracking the current page as we pass each marker.
    current_page = 1
    word_pages = []
    for word in words:
        m = re.fullmatch(r"\[Page_(\d+)\]", word)
        if m:
            current_page = int(m.group(1))
        word_pages.append(current_page)

    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + CHUNK_SIZE]
        pages_in_chunk = word_pages[i : i + CHUNK_SIZE]

        first_page = pages_in_chunk[0]
        last_page = pages_in_chunk[-1]
        page_label = f"[Page {first_page}]" if first_page == last_page else f"[Pages {first_page}-{last_page}]"

        # Restore readable "[Page N]" markers inside the chunk body.
        body = " ".join(chunk_words).replace("[Page_", "[Page ")
        chunk_text = f"{page_label} [Source: {filename}]\n" + body
        chunks.append({
            "text": chunk_text,
            "source": filename,
            "pages": (first_page, last_page),
        })
        i += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def build_index(docs: list[ParsedDoc]) -> tuple:
    """
    Chunks all document text, embeds each chunk, and builds a FAISS index.
    Returns (index, chunks) — store both in session state after upload.
    """
    import faiss   # deferred — only needed once documents are being indexed

    all_chunks = []
    for doc in docs:
        if doc.raw_text:
            all_chunks.extend(_chunk_text(doc.raw_text, doc.filename))

    if not all_chunks:
        return None, []

    model = _get_model()
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalised vectors = cosine similarity
    index.add(embeddings.astype(np.float32))

    return index, all_chunks


# Matches explicit page references: "page 7", "pg 7", "page no. 7", and the
# citation form "(p.7, ...)" that our own chat prompt asks Gemini to answer with.
_PAGE_REF = re.compile(r"\b(?:page|pg)\.?\s*(?:no\.?\s*)?(\d+)\b|\(p\.\s*(\d+)", re.IGNORECASE)


def _find_page_refs(text: str) -> set[int]:
    pages = set()
    for m in _PAGE_REF.finditer(text):
        num = m.group(1) or m.group(2)
        pages.add(int(num))
    return pages


def query(question: str, index, chunks: list[dict], top_k: int = 20,
          page_hint_text: str = None, source_filter: str = None) -> str:
    """
    Retrieve the chunks most relevant to the question and return them as one
    formatted string for the Gemini prompt.

    Two retrieval signals are combined:
      1. Semantic search (FAISS / embeddings) — matches on meaning.
      2. Explicit page lookup — if the question (or page_hint_text) names a page
         ("what does page 7 say?", or a prior answer citing "(p.7, ...)"), we pull
         the chunks on that page DIRECTLY by their stored page range. Semantic
         search alone can't do this reliably: a page number carries little
         semantic similarity to the page's actual content, and a short OCR
         fragment (like a date next to a logo) can get buried in a chunk whose
         embedding is dominated by unrelated surrounding text.

    page_hint_text lets the caller widen page detection beyond the bare question —
    e.g. including the assistant's last reply, so a follow-up like "when was it
    signed?" still resolves to the page the previous answer already cited.

    source_filter restricts every result to chunks from a single document (by
    filename) — used by the Page 3 detailed view so the chat only sees that file.
    When set, we search the whole index and then keep only that document's chunks,
    so a small document still gets its most relevant passages rather than being
    crowded out by other files.

    Page-referenced chunks are listed first, then the semantic matches.
    """
    if index is None or not chunks:
        return ""

    def _ok(i: int) -> bool:
        return source_filter is None or chunks[i].get("source") == source_filter

    model = _get_model()
    q_embedding = model.encode([question], normalize_embeddings=True)
    # When filtering to one document, rank over the whole index then keep that
    # document's hits; otherwise just take the top_k globally.
    search_k = len(chunks) if source_filter else top_k
    scores, indices = index.search(q_embedding.astype(np.float32), search_k)
    selected = [int(i) for i in indices[0] if i >= 0 and _ok(int(i))][:top_k]

    # Pull chunks for any page named explicitly — in the question itself, or in
    # page_hint_text (capped so a request for a long page doesn't flood the prompt).
    requested_pages = _find_page_refs(question)
    if page_hint_text:
        requested_pages |= _find_page_refs(page_hint_text)
    if requested_pages:
        page_hits = [
            i for i, c in enumerate(chunks)
            if _ok(i) and c.get("pages") and any(c["pages"][0] <= p <= c["pages"][1] for p in requested_pages)
        ][:6]
        # Page hits first, then semantic matches not already included.
        ordered = page_hits + [i for i in selected if i not in page_hits]
    else:
        ordered = selected

    results = [chunks[i]["text"] for i in ordered if 0 <= i < len(chunks)]
    return "\n\n---\n\n".join(results)
