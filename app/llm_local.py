"""Local quantised-LLM backend for NutriMind AI (final semester).

Runs a 4-bit (Q4_K_M) GGUF model on the CPU through ``llama-cpp-python``, giving
the AI layer zero API cost, full data privacy and offline operation — the
headline contribution described in ``docs/07_QUANTIZATION_ROADMAP.md``.

Two rules shape this module:

1. **Nothing loads at import time.** A 7B Q4_K_M model takes several seconds and
   ~5 GB of RAM to map, so the ``Llama`` object is built lazily on the first
   generation call and then cached for the process lifetime. ``import
   app.llm_local`` stays instant, and ``uvicorn`` start-up is unaffected.
2. **It never raises.** ``llama-cpp-python`` may not be installed, the GGUF may
   not have been downloaded, the machine may be out of memory. Every public
   helper returns ``None``/``False`` instead of propagating, so ``ai.py`` can
   fall through to the Groq tier and then to the deterministic rule-based tier.

Public surface:
    ``available()``      - cheap "could we use the local tier?" check
    ``chat()``           - free-text completion, returns ``str`` or ``None``
    ``chat_json()``      - Pydantic-validated structured output, or ``None``
    ``status()``         - diagnostics for ``/api/health``
    ``unload()``         - release the model (tests / RAM pressure)
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import threading
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from .setup_model import (find_any_gguf, is_usable_gguf, model_path,
                          resolve_model_spec)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Lazy singleton state
# ---------------------------------------------------------------------------
_LOCK = threading.RLock()
_LLM: Any = None
_LOAD_ATTEMPTED = False        # latch: never re-attempt a load that failed
_LOAD_ERROR: Optional[str] = None
_LOADED_PATH: Optional[str] = None

DEFAULT_CTX = 4096
DEFAULT_MAX_TOKENS = 512


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        raw = _env(name)
        return int(raw) if raw else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Availability (cheap — must not import llama_cpp or touch the weights)
# ---------------------------------------------------------------------------
def llama_cpp_available() -> bool:
    """True if ``llama-cpp-python`` is importable, without importing it."""
    try:
        return importlib.util.find_spec("llama_cpp") is not None
    except (ImportError, ValueError):
        return False


def resolve_path() -> Optional[str]:
    """Absolute path of the GGUF to load, or ``None`` if none is on disk.

    Order: explicit ``LOCAL_MODEL_PATH`` -> the RAM-resolved spec filename ->
    the largest ``*.gguf`` in ``models/`` (so a self-quantised file produced by
    ``quantize_model.py`` is picked up without extra configuration).
    """
    explicit = _env("LOCAL_MODEL_PATH")
    if explicit:
        return os.path.abspath(explicit) if os.path.isfile(explicit) else None

    expected = model_path()
    if os.path.isfile(expected):
        return expected

    return find_any_gguf()


def model_downloaded() -> bool:
    return resolve_path() is not None


def available() -> bool:
    """True if the local tier *could* serve a request right now.

    Cheap by design — used by ``ai_mode()`` and ``/api/health``. It does not
    prove the model loads (that needs several seconds and gigabytes); a load
    failure is caught at call time and latched into :func:`status`.
    """
    if _LOAD_ATTEMPTED and _LLM is None:
        return False       # we already tried and it failed — stop advertising it
    return llama_cpp_available() and model_downloaded()


def is_loaded() -> bool:
    return _LLM is not None


# ---------------------------------------------------------------------------
# Lazy load
# ---------------------------------------------------------------------------
def get_llm() -> Any:
    """Return the cached ``Llama`` instance, loading it on first use.

    Returns ``None`` (never raises) if the package is missing, the GGUF is
    absent, or the load itself fails. The failure is latched so we pay the cost
    at most once per process instead of stalling every request.
    """
    global _LLM, _LOAD_ATTEMPTED, _LOAD_ERROR, _LOADED_PATH

    if _LLM is not None:
        return _LLM
    if _LOAD_ATTEMPTED:
        return None

    with _LOCK:
        if _LLM is not None:
            return _LLM
        if _LOAD_ATTEMPTED:
            return None
        _LOAD_ATTEMPTED = True

        path = resolve_path()
        if not path:
            _LOAD_ERROR = ("no GGUF model found — run "
                           "'python -m app.setup_model'")
            return None
        if not llama_cpp_available():
            _LOAD_ERROR = ("llama-cpp-python is not installed — run "
                           "'pip install -r requirements.txt'")
            return None

        try:
            from llama_cpp import Llama  # heavy import: only inside the lock

            threads = _env_int("LOCAL_MODEL_THREADS", 0)
            kwargs = {
                "model_path": path,
                "n_ctx": _env_int("LOCAL_MODEL_CTX", DEFAULT_CTX),
                "n_gpu_layers": _env_int("LOCAL_MODEL_GPU_LAYERS", 0),
                "n_batch": _env_int("LOCAL_MODEL_BATCH", 512),
                "verbose": _env_bool("LOCAL_MODEL_VERBOSE", False),
            }
            if threads > 0:
                kwargs["n_threads"] = threads

            _LLM = Llama(**kwargs)
            _LOADED_PATH = path
            _LOAD_ERROR = None
        except Exception as exc:      # missing DLL, OOM, corrupt GGUF, ...
            _LLM = None
            _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        return _LLM


def unload() -> None:
    """Drop the cached model and clear the failure latch (tests, RAM pressure)."""
    global _LLM, _LOAD_ATTEMPTED, _LOAD_ERROR, _LOADED_PATH
    with _LOCK:
        _LLM = None
        _LOAD_ATTEMPTED = False
        _LOAD_ERROR = None
        _LOADED_PATH = None


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------
def chat(prompt: str, system: Optional[str] = None, temperature: float = 0.4,
         max_tokens: int = DEFAULT_MAX_TOKENS,
         stop: Optional[list] = None) -> Optional[str]:
    """Single-turn chat completion. Returns the text, or ``None`` on any failure.

    ``llama-cpp-python`` applies the chat template baked into the GGUF, so the
    same call works for Mistral-Instruct and Phi-3-mini without prompt-format
    changes here.
    """
    llm = get_llm()
    if llm is None:
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        with _LOCK:      # llama.cpp contexts are not re-entrant across threads
            out = llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop or [],
            )
        text = (out["choices"][0]["message"].get("content") or "").strip()
        return text or None
    except Exception:
        return None


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort JSON object recovery from a model response.

    Grammar-constrained decoding usually returns clean JSON, but smaller
    quantised models sometimes wrap it in prose or a ```json fence.
    """
    if not text:
        return None
    candidate = text.strip()

    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except (ValueError, TypeError):
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(candidate[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def chat_json(prompt: str, schema: Type[T], system: Optional[str] = None,
              temperature: float = 0.2,
              max_tokens: int = DEFAULT_MAX_TOKENS) -> Optional[T]:
    """Structured output: generate JSON matching ``schema`` and validate it.

    Uses llama.cpp's GBNF grammar support (``response_format`` with a JSON
    schema) so the sampler can only emit conforming tokens — the local
    equivalent of LangChain's ``with_structured_output``. If the installed build
    rejects the schema, it retries in plain ``json_object`` mode and validates
    with Pydantic instead. Returns ``None`` on any failure so the caller can
    fall through to the next tier.
    """
    llm = get_llm()
    if llm is None:
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({
        "role": "user",
        "content": prompt + "\n\nReply with a single JSON object only.",
    })

    try:
        json_schema = schema.model_json_schema()
    except Exception:
        json_schema = None

    formats = []
    if json_schema:
        formats.append({"type": "json_object", "schema": json_schema})
    formats.append({"type": "json_object"})

    for response_format in formats:
        try:
            with _LOCK:
                out = llm.create_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            text = out["choices"][0]["message"].get("content") or ""
        except Exception:
            continue

        data = _extract_json(text)
        if data is None:
            continue
        try:
            return schema.model_validate(data)
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
def status() -> dict:
    """Machine-readable state of the local tier, for ``/api/health``.

    Never loads the model — ``loaded`` reflects whether a previous request
    already paid that cost.
    """
    spec = resolve_model_spec()
    path = _LOADED_PATH or resolve_path()
    size_gb = None
    if path:
        try:
            size_gb = round(os.path.getsize(path) / (1024 ** 3), 2)
        except OSError:
            size_gb = None
    return {
        "available": available(),
        "llama_cpp_installed": llama_cpp_available(),
        "model_downloaded": path is not None,
        "loaded": is_loaded(),
        "model_path": path,
        "model_file": os.path.basename(path) if path else spec.filename,
        "model_repo": spec.repo_id,
        "model_tier": spec.tier,
        "model_size_gb": size_gb,
        "quantisation": "Q4_K_M",
        "n_ctx": _env_int("LOCAL_MODEL_CTX", DEFAULT_CTX),
        "error": _LOAD_ERROR,
    }
