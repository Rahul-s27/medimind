# RAG pipeline: retrieval and generation (modern chains)
from __future__ import annotations

import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from datetime import timedelta
import re

# HTTP + caching and extraction for web fallback
import requests
import requests_cache
import trafilatura
from bs4 import BeautifulSoup
import openai
from urllib.parse import urlparse
from web_fetcher import filter_trusted

load_dotenv()

PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
# Use a fresh collection name for the new 1024-dim embeddings
COLLECTION = "hc_docs_mrl"

# No need to remap OPENAI_* env vars; we pass api_key/base_url directly to ChatOpenAI

# Embeddings + VectorStore (community packages)
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS


# Chat model via OpenAI-compatible client pointing to OpenRouter
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.schema import Document

DEFAULT_MODEL = os.getenv("RAG_MODEL", "openrouter/auto")
DEFAULT_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "3000"))
WEB_CACHE_TTL_HOURS = int(os.getenv("WEB_CACHE_TTL_HOURS", "24"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Trusted domains for live medical retrieval
TRUSTED_DOMAINS = ("who.int", "cdc.gov", "nih.gov", "medlineplus.gov", "pubmed.ncbi.nlm.nih.gov")

# Install a persistent cached session for web fetches
requests_cache.install_cache(
    cache_name="web_cache",
    backend="sqlite",
    expire_after=timedelta(hours=WEB_CACHE_TTL_HOURS),
)

# Allowed models (keep in sync with /models endpoint in app.py)
ALLOWED_MODELS = {
    "moonshotai/kimi-vl-a3b-thinking:free",
    "openrouter/auto",
    "qwen/qwen2.5-vl-32b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
}


def _get_llm(model: str | None = None, temperature: float = 0.1, max_tokens: int | None = None):
    return ChatOpenAI(
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        timeout=120,
        max_retries=2,
    )


# create a document-combiner (stuff) and retrieval chain

# Some providers (e.g., google/gemma via OpenRouter) do not support a system role.
# Build prompts conditionally.
_SYSTEM_INSTRUCTION = (
    "You are a concise, cautious medical assistant. When uncertain, say you are not a doctor "
    "and recommend clinical consult. Use only the provided source documents."
)

_prompt_with_system = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_INSTRUCTION),
    ("user", "{input}\n\nContext:\n{context}"),
])

_prompt_user_only = ChatPromptTemplate.from_messages([
    (
        "user",
        _SYSTEM_INSTRUCTION
        + "\n\nQuestion: {input}\n\nContext:\n{context}"
    ),
])

def _supports_system_role(model: str | None) -> bool:
    if not model:
        return True
    # Known case: Google Gemma via OpenRouter rejects system/developer instruction
    return not model.startswith("google/gemma")


def _get_prompt_for_model(model: str | None) -> ChatPromptTemplate:
    return _prompt_with_system if _supports_system_role(model) else _prompt_user_only


def _build_chain(model: str | None = None, temperature: float = 0.1, max_tokens: int | None = None):
    llm = _get_llm(model=model, temperature=temperature, max_tokens=max_tokens)
    prompt = _get_prompt_for_model(model)
    doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    return create_retrieval_chain(retriever=retriever, combine_docs_chain=doc_chain)


def _source_title_from_meta(meta: dict) -> str:
    # Prefer explicit title
    title = meta.get("title")
    if title:
        return str(title)
    src = meta.get("source") or meta.get("file_path") or meta.get("path") or "unknown"
    if isinstance(src, str) and src.startswith("http"):
        try:
            u = urlparse(src)
            return (u.netloc or "web").replace("www.", "")
        except Exception:
            return "web"
    # fallback to filename
    try:
        return str(src).split("/")[-1]
    except Exception:
        return "unknown"


def _similar_sources(question: str, k: int) -> list[tuple]:
    """Query Chroma directly for top-k with scores and return (doc, score)."""
    try:
        results = db.similarity_search_with_score(question, k=k)
        return results  # list of (Document, score)
    except Exception:
        return []


def _google_search_trusted(query: str, max_results: int = 5) -> list[str]:
    # Removed Google CSE integration; return empty to indicate unsupported
    return []


# -------- Web fallback utilities (now prefers Tavily) --------
def _tavily_search(query: str, max_results: int = 20) -> list[str]:
    if not TAVILY_API_KEY:
        return []
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "include_answer": False,
                "max_results": max_results,
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json() or {}
        urls = []
        for item in data.get("results", [])[:max_results]:
            url = item.get("url")
            if url:
                urls.append(url)
        # Dedup while preserving order
        seen, out = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out
    except Exception:
        return []
def _ddg_search_trusted(query: str, max_results: int = 5) -> list[str]:
    results = []
    try:
        for r in DDGS().text(query, max_results=max_results):
            url = r.get("href") or r.get("url")
            if not url:
                continue
            if any(d in url for d in TRUSTED_DOMAINS):
                results.append(url)
    except Exception:
        pass
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for u in results:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _serpapi_search_trusted(query: str, max_results: int = 5) -> list[str]:
    # Removed SerpAPI integration; return empty to indicate unsupported
    return []


def _search_trusted(query: str, max_results: int = 12) -> list[str]:
    # Provider preference: Tavily -> DuckDuckGo (DDGS)
    urls = _tavily_search(query, max_results=max_results)
    if urls:
        return urls
    return _ddg_search_trusted(query, max_results=max_results)


def _fetch_and_extract(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        html = resp.text
        # First try trafilatura
        downloaded = trafilatura.extract(html, include_comments=False, include_tables=False)
        if downloaded and len(downloaded.strip()) > 200:
            return downloaded.strip()
        # Fallback to BeautifulSoup-based cleaning
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.extract()
        text = soup.get_text(separator="\n")
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if len(cleaned) > 200:
            return cleaned
    except Exception:
        return None
    return None


def _web_fallback_docs(question: str, max_pages: int = 12) -> list[Document]:
    """Fetch trusted web pages and return as LangChain Documents.
    Uses `_search_trusted` to find URLs, then `_fetch_and_extract` to get clean text.
    """
    docs: list[Document] = []
    try:
        urls = _search_trusted(question, max_results=max_pages)
    except Exception:
        urls = []
    for url in urls:
        try:
            content = _fetch_and_extract(url)
            if not content or len(content.strip()) < 200:
                continue
            meta = {"source": url}
            try:
                u = urlparse(url)
                if u.netloc:
                    meta["title"] = u.netloc.replace("www.", "")
            except Exception:
                pass
            docs.append(Document(page_content=content.strip(), metadata=meta))
            if len(docs) >= max_pages:
                break
        except Exception:
            continue
    return docs


def _shrink_documents(
    docs: list[Document],
    *,
    max_docs: int = 8,
    max_chars_per_doc: int = 1500,
    total_char_limit: int = 8000,
) -> list[Document]:
    """Cap number and size of documents to keep prompt within token budget.
    Roughly assumes 4 chars ~= 1 token. Adjust as needed.
    """
    if not docs:
        return []
    out: list[Document] = []
    used = 0
    for d in docs[:max_docs]:
        text = (d.page_content or "").strip()
        if not text:
            continue
        # Trim per-doc
        if len(text) > max_chars_per_doc:
            text = text[:max_chars_per_doc]
        # Enforce total cap
        remain = total_char_limit - used
        if remain <= 0:
            break
        if len(text) > remain:
            text = text[:remain]
        used += len(text)
        out.append(Document(page_content=text, metadata=d.metadata))
    return out

def _format_sources_from_docs(docs: list[Document], *, question: str | None = None) -> list[dict]:
    """Turn Documents into UI-friendly sources: [{title, url, snippet}]."""
    out: list[dict] = []
    # Optional similarity map if needed in future
    for d in docs:
        meta = getattr(d, "metadata", None) or {}
        src = meta.get("source") or meta.get("file_path") or meta.get("path") or "unknown"
        title = _source_title_from_meta(meta)
        snippet = (getattr(d, "page_content", "") or "").strip()[:280]
        out.append({
            "title": title,
            "url": src if isinstance(src, str) and src.startswith("http") else None,
            "snippet": snippet if snippet else None,
        })
    # Deduplicate by (title,url,snippet)
    dedup: list[dict] = []
    seen: set[tuple] = set()
    for s in out:
        sig = (s.get("title"), s.get("url"), s.get("snippet"))
        if sig in seen:
            continue
        seen.add(sig)
        dedup.append(s)
    return dedup


def answer_direct(
    question: str,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.1,
) -> str:
    """Direct LLM reasoning (no retrieval, no web). Returns text only."""
    # Normalize/validate requested model
    if model and model not in ALLOWED_MODELS:
        model = DEFAULT_MODEL
    llm = _get_llm(model=model, temperature=temperature, max_tokens=max_tokens)
    # Reuse shared prompt builder that always includes {context}
    prompt = _get_prompt_for_model(model)
    doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    out = doc_chain.invoke({"input": question, "context": []})
    if isinstance(out, dict):
        return out.get("answer") or out.get("output_text") or out.get("result") or str(out)
    return str(out)


def answer(
    question: str,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.1,
    web_max_results: int | None = None,
) -> Dict[str, Any]:
    """Run web-based retrieval and generation and return {answer, sources}."""
    # Normalize/validate requested model
    if model and model not in ALLOWED_MODELS:
        model = DEFAULT_MODEL

    web_docs = _web_fallback_docs(question, max_pages=(web_max_results or 12))
    web_docs = _shrink_documents(web_docs)
    llm = _get_llm(model=model, temperature=temperature, max_tokens=max_tokens)
    prompt = _get_prompt_for_model(model)
    doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    web_out = doc_chain.invoke({"input": question, "context": web_docs})
    web_text = (
        web_out.get("answer") if isinstance(web_out, dict) else str(web_out)
    )
    web_sources = _format_sources_from_docs(web_docs, question=question)
    return {"answer": web_text, "sources": web_sources}
