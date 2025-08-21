from fastapi import FastAPI, Form, File, UploadFile
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import rag
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from router import ask_llm
import tempfile
import os


def _to_structured(
    answer_text: str,
    sources: List[Dict[str, Any]] | None = None,
    *,
    title: str | None = None,
    summary: str | None = None,
) -> Dict[str, Any]:
    """Create a structured payload from free text and optional sources.
    Keeps an 'answer' field for backward-compat with existing frontends.
    """
    txt = (answer_text or '').strip()
    # Simple summary and points heuristic (can be overridden)
    computed_summary = txt[:200] + ('...' if len(txt) > 200 else '')
    # Try to split into bullet-like points
    raw_points = []
    for sep in ['\n- ', '\n• ', '\n* ']:
        if sep in txt:
            raw_points = [p.strip() for p in txt.split(sep) if p.strip()]
            break
    if not raw_points:
        # Fallback: split by sentences (very light)
        raw_points = [s.strip() for s in txt.replace('\n', ' ').split('. ') if s.strip()]
        raw_points = raw_points[:5]
    points = raw_points[:6]

    # Normalize sources
    norm_sources: List[Dict[str, Any]] = []
    if sources:
        for s in sources:
            norm_sources.append({
                'title': s.get('title') or s.get('name') or 'Source',
                'url': s.get('url') or s.get('link') or '',
                'raw_content': s.get('raw_content') or s.get('snippet') or ''
            })

    return {
        'title': title or 'AI Response',
        'summary': summary or computed_summary,
        'points': points,
        'sources': norm_sources,
        'answer': txt,  # backward-compat
    }

app = FastAPI()

origins = [
    "http://localhost:5173",  # React dev server
    "https://yourdomain.com",
    "https://medimind.vercel.app" # Production domain
]
# Allow CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only! Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")

class AskRequest(BaseModel):
    question: str
    k: Optional[int] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    mode: Optional[str] = None  # "ai" for direct LLM, else RAG
    use_rag: Optional[bool] = False  # for web mode: also consult PDFs/vector store
    max_results: Optional[int] = None  # for web mode: number of web sources


@app.post("/ask")
def ask(req: AskRequest):
    """Run either direct LLM (ai mode) or RAG (default/web mode)."""
    temperature = req.temperature if req.temperature is not None else 0.1
    mode = (req.mode or "").lower()
    if mode == "ai":
        text = rag.answer_direct(
            req.question,
            model=req.model,
            max_tokens=req.max_tokens,
            temperature=temperature,
        )
        return _to_structured(text, [], title="AI Response")
    # Default to RAG/web pipeline
    result = rag.answer(
        req.question,
        k=req.k,
        model=req.model,
        max_tokens=req.max_tokens,
        temperature=temperature,
        use_rag=bool(req.use_rag),
        web_max_results=req.max_results,
    )
    # Expected shape from rag.answer: {"answer": str, "sources": [..]}
    ans_text = result.get('answer') if isinstance(result, dict) else str(result)
    srcs = result.get('sources', []) if isinstance(result, dict) else []
    return _to_structured(
        ans_text,
        srcs,
        title=f"Search Results for '{req.question}'",
        summary="Here are the latest trusted sources for your query.",
    )


@app.get("/models")
def list_models():
    """Return a curated list of OpenRouter model IDs for selection in the frontend dropdown."""
    return {
        "models": [
            # Requested/free options
            "moonshotai/kimi-vl-a3b-thinking:free",
            "openrouter/auto",  # automatic free fallback
            "qwen/qwen2.5-vl-32b-instruct:free",
            "deepseek/deepseek-chat-v3-0324:free",
        ]
    }


@app.get("/")
def root():
    return {"message": "AI Healthcare Backend is running"}


@app.post("/ask-form")
async def ask_form(
    question: str = Form(...),
    mode: str = Form(...),  # "ai" or "web"
    model: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    """Form-data variant for simple HTML clients. Supports optional image for AI mode.
    Uses existing models; does not alter curated list.
    """
    mode_l = (mode or "").lower()
    # Default model if none provided
    chosen_model = model
    if mode_l == "ai":
        # If an image is provided, use ask_llm directly with image file path
        if image is not None:
            # Persist upload to a temp file to pass a path to ask_llm
            suffix = os.path.splitext(image.filename or "upload")[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await image.read()
                tmp.write(content)
                tmp_path = tmp.name
            try:
                answer_text = ask_llm(chosen_model or "openrouter/auto", question, tmp_path)
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        else:
            # No image; use direct LLM path already in RAG module
            answer_text = rag.answer_direct(
                question,
                model=chosen_model,
                max_tokens=None,
                temperature=0.1,
            )
        return _to_structured(answer_text, [], title="AI Response")
    # Web mode -> use RAG; image is currently ignored
    result = rag.answer(
        question,
        k=None,
        model=chosen_model,
        max_tokens=None,
        temperature=0.1,
        use_rag=False,
        web_max_results=None,
    )
    ans_text = result.get('answer') if isinstance(result, dict) else str(result)
    srcs = result.get('sources', []) if isinstance(result, dict) else []
    return _to_structured(
        ans_text,
        srcs,
        title=f"Search Results for '{question}'",
        summary="Here are the latest trusted sources for your query.",
    )