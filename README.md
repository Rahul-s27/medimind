🏥 MediMindAI - LLM Powered Healthcare Assistant

An intelligent personalized healthcare assistant that leverages LLMs and RAG (Retrieval-Augmented Generation) to provide symptom analysis, medical document understanding, and real-time triage support through a secure web interface.

🚀 Features

🔑 Google Authentication – Secure login for users.
💬 Symptom Checker – AI-driven health triage powered by LLM-based reasoning.
📄 Document Analysis – Upload and analyze medical documents (PDF, reports, prescriptions) with OCR + NLP.
📚 RAG-Enhanced Responses – Uses a retrieval pipeline with ChromaDB to fetch accurate, evidence-based medical context before generating LLM answers.
🤖 Multimodal AI – Combines text + documents for a comprehensive healthcare assistant.
⚡ Real-Time Chat – Streaming responses from the backend AI agent.

🧠 How RAG + LLM Works

Document Ingestion – Medical literature, PDFs, and research articles are stored in a vector database (ChromaDB).
Query Processing – User’s symptoms or uploaded reports are converted into embeddings.
Retrieval Step – Relevant documents are retrieved using semantic search.
Augmented LLM Generation – The retrieved context is passed into the LLM (via OpenRouter/Gemini/LLAMA/Qwen) to produce accurate, context-aware medical insights.
This ensures the assistant is factual, explainable, and medically relevant instead of relying only on generic LLM responses.

🛠 Tech Stack
🔹 Backend (FastAPI)

FastAPI – Core backend framework.
ChromaDB – Vector database for RAG.
LangChain – Orchestration of RAG + LLM calls.
OCR/NLP – For medical document analysis.
JWT Auth + Google OAuth2 – Secure authentication.

🔹 Frontend (React + Vite + TypeScript)

React components for chat & document uploads.
Google Sign-In integration.
Real-time streaming chat UI.

🔹 AI / LLM

LLMs via OpenRouter (Gemini, LLaMA, Qwen, Mistral).
Retrieval-Augmented Generation (RAG) with LangChain + ChromaDB.

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

