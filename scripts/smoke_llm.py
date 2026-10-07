"""One real JSON-mode call through services.llm (key from .streamlit/secrets.toml).
Run: .venv/Scripts/python -m scripts.smoke_llm"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.config import get_settings  # noqa: E402
from services.llm import call_llm_json  # noqa: E402
from services.schemas import ConditionsOut  # noqa: E402

SECTION = ("(3) No person shall carry out or commence any preparatory work relating to any activity or part "
           "thereof specified in subsection (1) or any order made under it unless the Board has approved the report.")

if __name__ == "__main__":
    s = get_settings()
    print(f"provider={s.llm_provider} model={s.llm_model} fallbacks={list(s.llm_fallback_models)}")
    t = time.perf_counter()
    out, model = call_llm_json(
        "smoke",
        'Return a json object {"conditions":[{"key":string,"requirement":string,"why":string,"quote":string}],'
        '"explanation":string}. Quote 8-30 words copied exactly from the SECTION. Output json only.',
        f"ACTION: Council will build a waste recycling facility.\nSECTIONS:\n[KEY NREO:11A]\n{SECTION}",
        ConditionsOut)
    print(f"answered by {model} in {time.perf_counter() - t:.1f}s")
    print(out.model_dump_json(indent=2))
