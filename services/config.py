"""Settings and constants for the services package.

Settings are read in this order: environment variables -> Streamlit secrets (only when the
code runs inside a Streamlit app) -> .streamlit/secrets.toml -> .env -> defaults.
"""
from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAW_DIR = ROOT / "Law"
CATALOG_DIR = Path(__file__).resolve().parent / "catalog"

# Limits
MIN_ACTION_CHARS, MAX_ACTION_CHARS = 5, 2000
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MIN_CHARS_PER_PAGE = 50          # below this on average, treat the PDF as scanned
MAX_SECTION_CHARS = 6000         # section text sent to the LLM
MAX_CANDIDATES = 10
TOC_PICKS = 5
TOC_LAWS = 4                     # laws whose table of contents is shown to the plan call
TOC_LINES_PER_LAW = 60
XREF_LIMIT = 3
TRIGGER_ID_OFFSET = 1_000_000
DIFF_TEXT_CHARS = 2000
AUDIT_LIMIT = 100

# Only these instrument types can create a mandatory (red) requirement. Anything else an officer
# uploads (meeting minutes, circulars, guidelines, SOPs) is internal guidance: at most yellow.
LEGAL_INSTRUMENTS = {"Act", "Ordinance", "Constitution", "Amendment Act", "Subsidiary legislation",
                     "Order", "Rules", "Regulations", "Enactment"}

# Severity patterns, checked in order (first match wins; red before yellow).
SEVERITY_RED = [
    r"\bno person shall\b", r"\bshall not\b", r"\bshall\b", r"\bmust\b",
    r"\bguilty of an offence\b", r"\bcommits an offence\b", r"\bliable to\b", r"\bpenalt(?:y|ies)\b",
    # Bahasa Melayu
    r"\btiada seorang pun boleh\b", r"\btidak boleh\b", r"\bhendaklah\b",
    r"\bmelakukan suatu kesalahan\b", r"\bboleh didenda\b", r"\bpenalti\b",
]
SEVERITY_YELLOW = [
    r"\bmay\b", r"\bsubject to\b", r"\bthinks? fit\b", r"\bdeems? (?:fit|necessary|desirable)\b",
    # Bahasa Melayu
    r"\bboleh\b", r"\btertakluk kepada\b", r"\bdifikirkan(?:nya)? patut\b",
]


def _secrets_file() -> dict:
    path = ROOT / ".streamlit" / "secrets.toml"
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _dotenv() -> dict:
    try:
        from dotenv import dotenv_values
        return dict(dotenv_values(ROOT / ".env"))
    except Exception:
        return {}


def _streamlit_secrets() -> dict:
    try:
        from streamlit import runtime
        if not runtime.exists():
            return {}
        import streamlit as st
        return {k: v for k, v in st.secrets.items() if isinstance(v, (str, int, float, bool))}
    except Exception:
        return {}


def _flag(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_fallback_models: tuple[str, ...]
    llm_max_tokens: int
    llm_timeout: float
    llm_reasoning_effort: str
    data_dir: Path
    catalog_file: Path
    fake_llm_dir: Path
    highlight: bool
    xrefs: bool
    keyword_k: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    sources = [os.environ, _streamlit_secrets(), _secrets_file(), _dotenv()]

    def get(name: str, default: str = "") -> str:
        for src in sources:
            value = src.get(name)
            if value not in (None, ""):
                return str(value)
        return default

    def path(name: str, default: Path) -> Path:
        p = Path(get(name, str(default)))
        return p if p.is_absolute() else ROOT / p

    return Settings(
        llm_provider=get("LLM_PROVIDER", "openai_compatible"),
        llm_base_url=get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
        llm_api_key=get("LLM_API_KEY"),
        llm_model=get("LLM_MODEL", "gemini-3.5-flash-lite"),
        llm_fallback_models=tuple(m.strip() for m in get("LLM_FALLBACK_MODELS").split(",") if m.strip()),
        llm_max_tokens=int(get("LLM_MAX_TOKENS", "3000")),
        llm_timeout=float(get("LLM_TIMEOUT", "40")),
        llm_reasoning_effort=get("LLM_REASONING_EFFORT"),
        data_dir=path("DATA_DIR", ROOT / "data"),
        catalog_file=path("CATALOG_FILE", CATALOG_DIR / "laws.json"),
        fake_llm_dir=path("FAKE_LLM_DIR", ROOT / "tests" / "fixtures" / "llm"),
        highlight=_flag(get("HIGHLIGHT", "1")),
        xrefs=_flag(get("XREFS", "1")),
        keyword_k=int(get("KEYWORD_K", "5")),
    )


@lru_cache(maxsize=1)
def tags() -> tuple[str, ...]:
    """The frontend's fixed activity tags (kept in catalog/triggers.json)."""
    data = json.loads((CATALOG_DIR / "triggers.json").read_text(encoding="utf-8"))
    return tuple(data["tags"])


def resolve_path(stored: str) -> Path:
    """DB paths are stored relative to the repo root when possible."""
    p = Path(stored)
    return p if p.is_absolute() else ROOT / p


def store_path(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p.resolve())
