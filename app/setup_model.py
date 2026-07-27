"""Automatic local-model provisioning for NutriMind AI (final semester).

Downloads a **pre-quantised GGUF** model from Hugging Face into ``models/`` so
the user never has to fetch, convert or quantise anything by hand. It is called
automatically by ``setup.bat`` after ``pip install`` and can be re-run safely at
any time:

    python -m app.setup_model            # download if missing
    python -m app.setup_model --check    # report only, download nothing
    python -m app.setup_model --force    # re-download even if present

Model choice is RAM-aware. A 7B-class Q4_K_M model (~4.4 GB on disk, ~5-6 GB
resident) is the dissertation target, but it is unusable on an 8 GB laptop that
is also running a browser, so machines with less than
``LOCAL_MODEL_MIN_RAM_GB`` (default 8 GB) of physical RAM automatically get the
3B-class Phi-3-mini build instead — the low-RAM fallback already named in
``docs/07_QUANTIZATION_ROADMAP.md``.

Nothing here is imported at application start-up: ``huggingface_hub`` is
imported lazily inside :func:`download_model`, so a missing dependency can never
break ``import app.main``. Every public helper degrades to a status dict rather
than raising, because setup must warn-and-continue (the app still works on the
Groq and rule-based tiers).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults (override any of these in .env)
# ---------------------------------------------------------------------------
# Primary: 7B-class instruct model, Q4_K_M — matches the dissertation
# commitment ("a 4-bit quantised 7B model on a laptop"). Apache-2.0, ungated.
DEFAULT_REPO = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
DEFAULT_FILE = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
DEFAULT_SIZE_GB = 4.4

# Low-RAM fallback: 3B-class (3.8B) instruct model, Q4_K_M. MIT, ungated.
SMALL_REPO = "microsoft/Phi-3-mini-4k-instruct-gguf"
SMALL_FILE = "Phi-3-mini-4k-instruct-q4.gguf"
SMALL_SIZE_GB = 2.4

# Below this much physical RAM we drop to the smaller model automatically.
DEFAULT_MIN_RAM_GB = 8.0

# Smallest file we will treat as a real model. An interrupted download leaves a
# short file behind, and handing that to llama.cpp is a hard crash, so anything
# below this is ignored everywhere (here and in llm_local.resolve_path).
MIN_MODEL_BYTES = 50 * 1024 * 1024

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Small env helpers (kept local so this module has no intra-package imports)
# ---------------------------------------------------------------------------
def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_float(name: str, default: float) -> float:
    try:
        raw = _env(name)
        return float(raw) if raw else default
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def models_dir() -> str:
    """Absolute path of the directory holding GGUF weights (created on demand)."""
    configured = _env("LOCAL_MODEL_DIR", "models")
    path = configured if os.path.isabs(configured) else os.path.join(
        PROJECT_ROOT, configured)
    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# RAM detection
# ---------------------------------------------------------------------------
def total_ram_gb() -> Optional[float]:
    """Physical RAM in GB, or ``None`` if it cannot be determined.

    Prefers ``psutil``; falls back to the Win32 ``GlobalMemoryStatusEx`` call
    and then to POSIX ``sysconf`` so the RAM check still works if the optional
    dependency was not installed.
    """
    try:
        import psutil  # type: ignore
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    if sys.platform.startswith("win"):
        try:
            import ctypes

            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MemoryStatusEx()
            stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return stat.ullTotalPhys / (1024 ** 3)
        except Exception:
            pass
    else:
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return (pages * page_size) / (1024 ** 3)
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Model spec resolution
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelSpec:
    """Which GGUF we intend to use, and why."""
    repo_id: str
    filename: str
    size_gb: float
    tier: str          # "7b" | "3b"
    reason: str

    @property
    def path(self) -> str:
        return os.path.join(models_dir(), self.filename)


def resolve_model_spec() -> ModelSpec:
    """Pick the GGUF to provision, honouring .env overrides then RAM.

    Resolution order:
      1. ``LOCAL_MODEL_REPO`` + ``LOCAL_MODEL_FILE``  -> used verbatim.
      2. RAM >= ``LOCAL_MODEL_MIN_RAM_GB``            -> 7B Q4_K_M (default).
      3. RAM below that (or unknown on a small box)   -> 3B Q4_K_M.
    Unknown RAM is treated as "big enough" so we still honour the dissertation
    default rather than silently downgrading.
    """
    repo = _env("LOCAL_MODEL_REPO")
    filename = _env("LOCAL_MODEL_FILE")
    if repo and filename:
        return ModelSpec(repo, filename, 0.0, "custom",
                         "configured via LOCAL_MODEL_REPO/LOCAL_MODEL_FILE")

    min_ram = _env_float("LOCAL_MODEL_MIN_RAM_GB", DEFAULT_MIN_RAM_GB)
    ram = total_ram_gb()

    small_repo = _env("LOCAL_MODEL_REPO_SMALL", SMALL_REPO)
    small_file = _env("LOCAL_MODEL_FILE_SMALL", SMALL_FILE)

    if ram is not None and ram < min_ram:
        return ModelSpec(
            small_repo, small_file, SMALL_SIZE_GB, "3b",
            f"detected {ram:.1f} GB RAM (< {min_ram:.0f} GB) — using the "
            "3B-class Q4_K_M build")

    detected = f"detected {ram:.1f} GB RAM" if ram is not None else \
        "RAM could not be detected (install psutil for an accurate check)"
    return ModelSpec(DEFAULT_REPO, DEFAULT_FILE, DEFAULT_SIZE_GB, "7b",
                     f"{detected} — using the 7B-class Q4_K_M build")


def model_path() -> str:
    """Absolute path where the resolved model is expected to live."""
    return resolve_model_spec().path


def is_usable_gguf(path: Optional[str]) -> bool:
    """True if ``path`` is a GGUF big enough to be a real model, not a stub."""
    if not path:
        return False
    try:
        return (os.path.isfile(path)
                and os.path.getsize(path) >= MIN_MODEL_BYTES)
    except OSError:
        return False


def model_present() -> bool:
    """True if a usable GGUF is already on disk (non-trivial size)."""
    return is_usable_gguf(model_path())


def find_any_gguf() -> Optional[str]:
    """Largest ``*.gguf`` in ``models/`` — lets a self-quantised file be used.

    ``quantize_model.py`` writes files with its own naming, so the local tier
    should still find them even when they do not match the resolved spec.
    """
    directory = models_dir()
    if not os.path.isdir(directory):
        return None
    candidates = []
    try:
        for name in os.listdir(directory):
            if not name.lower().endswith(".gguf"):
                continue
            full = os.path.join(directory, name)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size >= MIN_MODEL_BYTES:
                candidates.append((size, full))
    except OSError:
        return None
    if not candidates:
        return None
    return max(candidates)[1]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
def huggingface_hub_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("huggingface_hub") is not None


def download_model(spec: Optional[ModelSpec] = None, force: bool = False) -> str:
    """Fetch ``spec`` into ``models/`` and return the final path.

    Raises on failure — callers that must not fail (setup.bat, the app) should
    use :func:`ensure_model` instead. ``huggingface_hub`` renders its own
    progress bar on stderr; we bracket it with plain-English status lines so a
    non-technical user can see what is happening during a multi-GB download.
    """
    spec = spec or resolve_model_spec()
    target_dir = models_dir()
    os.makedirs(target_dir, exist_ok=True)

    from huggingface_hub import hf_hub_download  # lazy: optional dependency

    size_note = f" (~{spec.size_gb:.1f} GB)" if spec.size_gb else ""
    print(f"    repo : {spec.repo_id}")
    print(f"    file : {spec.filename}{size_note}")
    print(f"    into : {target_dir}")
    print("    This is a ONE-TIME download. Leave it running...")
    sys.stdout.flush()

    downloaded = hf_hub_download(
        repo_id=spec.repo_id,
        filename=spec.filename,
        local_dir=target_dir,
        force_download=force,
        token=_env("HF_TOKEN") or None,
    )
    return os.path.abspath(downloaded)


def ensure_model(force: bool = False, check_only: bool = False) -> dict:
    """Provision the local model, never raising.

    Returns a status dict with ``ok``, ``status`` (one of ``present``,
    ``downloaded``, ``missing``, ``skipped``, ``failed``), ``path`` and a
    human-readable ``message``. Designed so ``setup.bat`` can print the message
    and carry on regardless of the outcome.
    """
    spec = resolve_model_spec()
    ram = total_ram_gb()
    base = {
        "repo_id": spec.repo_id,
        "filename": spec.filename,
        "tier": spec.tier,
        "reason": spec.reason,
        "path": spec.path,
        "models_dir": models_dir(),
        "ram_gb": round(ram, 1) if ram is not None else None,
    }

    if model_present() and not force:
        try:
            gb = os.path.getsize(spec.path) / (1024 ** 3)
        except OSError:
            gb = 0.0
        return {**base, "ok": True, "status": "present",
                "message": f"Local model already present ({gb:.2f} GB) — "
                           "skipping download."}

    if check_only:
        return {**base, "ok": False, "status": "missing",
                "message": "Local model not downloaded yet."}

    if _env("NUTRIMIND_SKIP_MODEL_DOWNLOAD", "").lower() in ("1", "true", "yes"):
        return {**base, "ok": False, "status": "skipped",
                "message": "NUTRIMIND_SKIP_MODEL_DOWNLOAD is set — "
                           "not downloading."}

    if not huggingface_hub_available():
        return {**base, "ok": False, "status": "failed",
                "message": "huggingface_hub is not installed — run "
                           "'pip install -r requirements.txt' first."}

    try:
        path = download_model(spec, force=force)
    except Exception as exc:  # network, auth, disk-full, gated repo, ...
        return {**base, "ok": False, "status": "failed",
                "message": f"Download failed: {type(exc).__name__}: {exc}"}

    try:
        gb = os.path.getsize(path) / (1024 ** 3)
    except OSError:
        gb = 0.0
    return {**base, "ok": True, "status": "downloaded", "path": path,
            "message": f"Local model ready ({gb:.2f} GB) at {path}"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_report(result: dict) -> None:
    print()
    print("  Local AI model")
    print(f"    tier      : {result['tier']}")
    print(f"    reason    : {result['reason']}")
    print(f"    status    : {result['status']}")
    print(f"    path      : {result['path']}")
    print(f"    {result['message']}")
    print()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.setup_model",
        description="Download the pre-quantised local GGUF model for NutriMind AI.")
    parser.add_argument("--check", action="store_true",
                        help="report status only; download nothing")
    parser.add_argument("--force", action="store_true",
                        help="re-download even if the file already exists")
    parser.add_argument("--repo", help="override the Hugging Face repo id")
    parser.add_argument("--file", dest="filename",
                        help="override the GGUF filename inside the repo")
    args = parser.parse_args(argv)

    # Load .env so the CLI honours the same configuration as the app.
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    except Exception:
        pass

    if args.repo:
        os.environ["LOCAL_MODEL_REPO"] = args.repo
    if args.filename:
        os.environ["LOCAL_MODEL_FILE"] = args.filename

    free_gb = None
    try:
        free_gb = shutil.disk_usage(PROJECT_ROOT).free / (1024 ** 3)
    except OSError:
        pass

    spec = resolve_model_spec()
    if (free_gb is not None and spec.size_gb and not model_present()
            and free_gb < spec.size_gb + 1):
        print(f"  [WARN] Only {free_gb:.1f} GB free on this drive; the model "
              f"needs about {spec.size_gb:.1f} GB.")

    result = ensure_model(force=args.force, check_only=args.check)
    _print_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
