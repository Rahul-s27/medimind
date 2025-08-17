# web_fetcher.py
# API-first utilities to query medical sources (free endpoints)
# Uses NCBI API key if present for higher PubMed rate limits.

from __future__ import annotations

import os
from typing import List, Dict, Any
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

load_dotenv()

NCBI_KEY = os.getenv("NCBI_API_KEY")


def search_pubmed_ids(query: str, retmax: int = 20) -> List[str]:
    """Search PubMed for PMIDs using E-utilities esearch.
    Returns a list of PMID strings.
    """
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
    }
    if NCBI_KEY:
        params["api_key"] = NCBI_KEY
    r = requests.get(base, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])


def fetch_pubmed_summaries(pmids: List[str]) -> Dict[str, Any]:
    """Fetch PubMed summaries for a list of PMIDs via esummary.
    Returns JSON payload (mapping of result UIDs to summary records).
    """
    if not pmids:
        return {}
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    if NCBI_KEY:
        params["api_key"] = NCBI_KEY
    r = requests.get(base, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def search_europepmc(query: str, page_size: int = 10) -> Dict[str, Any]:
    """Search Europe PMC JSON service for OA/metadata.
    Returns JSON response.
    """
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
        f"query={quote_plus(query)}&format=json&pageSize={page_size}"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


# You can extend with WHO/CDC/ClinicalTrials specific API calls when you provide the exact endpoints.


# Removed Google Custom Search integration. Web search is handled via Tavily or DDGS in `rag.py`.


def filter_trusted(urls: list[str]) -> list[str]:
    """Filter URLs to a stable set of trusted medical domains."""
    from urllib.parse import urlparse
    trusted = {
        "who.int",
        "cdc.gov",
        "nih.gov",
        "medlineplus.gov",
        "pubmed.ncbi.nlm.nih.gov",
    }
    out = []
    for u in urls:
        try:
            host = urlparse(u).netloc.lower()
            # allow subdomains of trusted domains
            if any(host == d or host.endswith("." + d) for d in trusted):
                out.append(u)
        except Exception:
            continue
    return out
