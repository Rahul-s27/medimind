# Script to ingest files into Chroma DB

import os
from dotenv import load_dotenv
load_dotenv()

PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
# Use a fresh collection to store 1024-dim MRL embeddings to avoid conflicts with old 384-dim index
COLLECTION = "hc_docs_mrl"

# robust imports (some LangChain versions differ)
try:
    from langchain_community.document_loaders import PyPDFLoader
except Exception:  # fallback for older langchain
    from langchain.document_loaders import PyPDFLoader

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # fallback for older langchain
    from langchain.text_splitter import RecursiveCharacterTextSplitter

# Prefer community imports per LangChain v0.2 guidance, fallback to legacy
try:
    from langchain_community.embeddings import SentenceTransformerEmbeddings
except Exception:
    from langchain.embeddings import SentenceTransformerEmbeddings

try:
    from langchain_community.vectorstores import Chroma
except Exception:
    from langchain.vectorstores import Chroma

def _is_pdf(path: str) -> bool:
    return os.path.isfile(path) and path.lower().endswith(".pdf")

def _gather_pdfs(root: str):
    """Recursively collect all PDF file paths under root (or return [root] if it's a PDF)."""
    if _is_pdf(root):
        return [root]
    pdfs = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".pdf"):
                pdfs.append(os.path.join(dirpath, fn))
    return pdfs

def index_pdf(path):
    loader = PyPDFLoader(path)
    docs = loader.load()  # list of Document objects (keeps page metadata)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    embeddings = SentenceTransformerEmbeddings(model_name="static-retrieval-mrl-en-v1")
    db = Chroma.from_documents(
        chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION,
    )
    db.persist()
    print(f"Indexed {len(chunks)} chunks into {PERSIST_DIR}/{COLLECTION}")

def index_many(paths):
    """Index multiple PDFs in one batch write to reduce overhead and duplicate collections."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    all_chunks = []
    total_docs = 0
    for p in paths:
        loader = PyPDFLoader(p)
        docs = loader.load()
        total_docs += len(docs)
        chunks = splitter.split_documents(docs)
        all_chunks.extend(chunks)
    if not all_chunks:
        print("No content found to index.")
        return
    embeddings = SentenceTransformerEmbeddings(model_name="static-retrieval-mrl-en-v1")
    db = Chroma.from_documents(
        all_chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION,
    )
    db.persist()
    print(
        f"Indexed {len(all_chunks)} chunks from {len(paths)} PDF file(s) (pages: {total_docs}) into {PERSIST_DIR}/{COLLECTION}"
    )

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python index_docs.py <file.pdf | folder>")
        sys.exit(1)
    target = sys.argv[1]
    paths = _gather_pdfs(target)
    print(f"Scanning '{target}' -> found {len(paths)} PDF(s)")
    if not paths:
        print(f"No PDFs found at: {target}")
        sys.exit(1)
    if len(paths) == 1:
        index_pdf(paths[0])
    else:
        index_many(paths)
