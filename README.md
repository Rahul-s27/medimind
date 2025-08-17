MediMind — Real-time RAG + Hybrid LLM Healthcare Assistant

MediMind is a multimodal, secure healthcare assistant that performs real-time Retrieval-Augmented Generation (RAG): every user query can trigger live web retrieval (Tavily + DuckDuckGo), merge results with local PDF knowledge (RAG over Chroma/FAISS), and produce a structured, source-cited answer with a fallback to LLM reasoning. It supports text + image inputs, model routing per task, and streaming responses.

🚀 Key highlights (short)

Real-time web retrieval: Tavily (primary) + DuckDuckGo (secondary) called on each query.

Local RAG: user PDFs indexed into Chroma/FAISS for document grounding.

Hybrid orchestration: query → RAG lookup → (if needed) live web fetch → merge → LLM generation.

Model routing: multimodal, doc, web, and fallback models (configurable).

Streaming: token/partial streaming to frontend (SSE/ReadableStream).

Structured output: Markdown / JSON with title, summary, key_points, answer, sources[].

Security: Google OAuth sign-in, JWT sessions; PHI handling precautions.

Every time a user asks a question (in Web Mode):

The system first queries your local RAG (PDFs) for high-confidence hits.

If the RAG result is insufficient, the backend calls Tavily (and optionally DuckDuckGo) to fetch current web results (titles, snippets, URLs).

The backend fetches/extracts page content for the top N links, optionally chunks & embeds them on the fly, then merges those contexts with PDF context.

The assembled context is passed to the selected LLM (model routing). The LLM returns a structured answer with numbered citations and clickable links.

Optionally the response is streamed to the UI as it is generated.

This achieves fresh, up-to-date answers without waiting for batch re-indexing.

## ⚙️ Installation & Setup

### 🔹 Backend (FastAPI)

cd backend
python -m venv venv

venv\Scripts\activate   # On Windows

source venv/bin/activate  # On Mac/Linux

pip install -r requirements.txt

# Run FastAPI server
uvicorn app:app --reload

Frontend (React + Vite + TypeScript)

cd frontend

npm install

npm run dev

🔑 Environment Variables

Create a .env file inside backend/ with:

GOOGLE_CLIENT_ID=your_google_client_id

GOOGLE_CLIENT_SECRET=your_google_client_secret

JWT_SECRET=your_jwt_secret

AI_API_KEY=your_ai_model_api_key

