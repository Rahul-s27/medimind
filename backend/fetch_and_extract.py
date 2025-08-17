# fetch_and_extract.py
# Utilities to fetch and extract text from HTML and PDF content for live retrieval.

from __future__ import annotations

import tempfile
from typing import Optional

import requests
import trafilatura
from bs4 import BeautifulSoup
import fitz  # PyMuPDF


def extract_html_text(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch a URL and extract the main readable text.
    - Try trafilatura.fetch_url/extract first.
    - Fallback to requests + BeautifulSoup cleanup.
    Returns cleaned text or None.
    """
    try:
        html = trafilatura.fetch_url(url, timeout=timeout)
    except Exception:
        html = None
    if not html:
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            html = r.text
        except Exception:
            return None
    try:
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if text and len(text.strip()) > 200:
            return text.strip()
    except Exception:
        pass
    # Fallback to BeautifulSoup cleaning
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.extract()
        txt = soup.get_text(separator="\n")
        cleaned = "\n".join(line.strip() for line in txt.splitlines() if line.strip())
        if len(cleaned) > 200:
            return cleaned
    except Exception:
        return None
    return None


essence_pdf_mime = ("application/pdf",)

def download_pdf_and_extract_text(url: str, timeout: int = 20) -> Optional[str]:
    """Download a PDF to a temp file and extract text with PyMuPDF.
    Returns extracted text or None.
    """
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(r.content)
            tmp.flush()
            doc = fitz.open(tmp.name)
            out = []
            for p in doc:
                out.append(p.get_text("text"))
            return "\n\n".join(out)
    except Exception:
        return None
