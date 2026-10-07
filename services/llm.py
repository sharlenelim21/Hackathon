"""One function for every LLM call: JSON in, validated model out.

openai_compatible: Gemini (or DeepSeek/OpenAI/OpenRouter) through the OpenAI SDK, with model fallback:
a 429/5xx/timeout/empty reply moves on to the next model in LLM_FALLBACK_MODELS (the Gemini free
tier returned 503 'high demand' for several models during testing).
fake: canned JSON from FAKE_LLM_DIR/<name>.json (tests, and a labelled replay mode).
"""
from __future__ import annotations

import json
import logging
import re
import time

from pydantic import BaseModel, ValidationError

from .config import get_settings

log = logging.getLogger("services.llm")


class LLMError(Exception):
    pass


class _Transient(Exception):
    pass


_clients: dict = {}


def _client(s):
    from openai import OpenAI
    key = (s.llm_base_url, s.llm_api_key, s.llm_timeout)
    if key not in _clients:
        _clients[key] = OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key, timeout=s.llm_timeout, max_retries=0)
    return _clients[key]


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t


def _complete(s, model: str, system: str, user: str) -> str:
    from openai import APIConnectionError, APIStatusError, APITimeoutError
    kwargs = dict(model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                  response_format={"type": "json_object"}, temperature=0, max_tokens=s.llm_max_tokens)
    if s.llm_reasoning_effort:
        kwargs["reasoning_effort"] = s.llm_reasoning_effort
    try:
        resp = _client(s).chat.completions.create(**kwargs)
    except (APITimeoutError, APIConnectionError) as e:
        raise _Transient(type(e).__name__) from None
    except APIStatusError as e:
        if e.status_code in (401, 403):
            raise LLMError(f"LLM authentication failed (HTTP {e.status_code}); check LLM_API_KEY.") from None
        raise _Transient(f"HTTP {e.status_code}") from None
    content = (resp.choices[0].message.content or "") if resp.choices else ""
    if not content.strip():
        raise _Transient("empty reply")
    return content


def call_llm_json(name: str, system: str, user: str, schema: type[BaseModel]) -> tuple[BaseModel, str]:
    """Return (validated output, model that answered)."""
    s = get_settings()
    if s.llm_provider == "fake":
        data = json.loads((s.fake_llm_dir / f"{name}.json").read_text(encoding="utf-8"))
        return schema.model_validate(data), "fake"
    if s.llm_provider != "openai_compatible":
        raise LLMError(f"LLM_PROVIDER '{s.llm_provider}' is not supported here (use openai_compatible or fake).")
    if not s.llm_api_key:
        raise LLMError("LLM_API_KEY is not set.")
    models = [s.llm_model] + [m for m in s.llm_fallback_models if m != s.llm_model]
    deadline = time.monotonic() + max(75.0, 2 * s.llm_timeout)
    last = "no model answered"
    for model in models:
        prompt = user
        for _attempt in range(2):
            if time.monotonic() > deadline:
                raise LLMError(f"Timed out. Last error: {last}")
            try:
                content = _complete(s, model, system, prompt)
            except _Transient as e:
                last = f"{model}: {e}"
                log.warning("LLM %s unavailable (%s); trying next model", model, e)
                time.sleep(1)
                break
            try:
                result = schema.model_validate(json.loads(_strip_fences(content)))
                log.info("LLM %s answered '%s'", model, name)
                return result, model
            except (ValueError, ValidationError) as e:
                last = f"{model}: invalid JSON ({str(e)[:160]})"
                prompt = user + "\n\nYour previous reply was not valid. Return only one valid json object in the required format."
    raise LLMError(last)
