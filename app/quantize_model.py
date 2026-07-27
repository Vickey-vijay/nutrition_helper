"""End-to-end 4-bit quantisation pipeline: FP16 Hugging Face model -> GGUF Q4_K_M.

This is the *demonstrable* quantisation path for the dissertation. It performs
the real conversion described in ``docs/07_QUANTIZATION_ROADMAP.md`` §2 rather
than downloading someone else's finished artefact:

    1. Download the FP16 model from Hugging Face (~14 GB for a 7B model).
    2. Convert PyTorch/safetensors weights to GGUF FP16 with llama.cpp's
       ``convert_hf_to_gguf.py``.
    3. Quantise that GGUF to 4-bit with the ``llama-quantize`` binary.

Run it as::

    python -m app.quantize_model                      # full 7B pipeline
    python -m app.quantize_model --repo <hf-repo>     # any HF causal LM
    python -m app.quantize_model --quant Q5_K_M       # different bit-width
    python -m app.quantize_model --check              # report tooling only

The resulting ``*.Q4_K_M.gguf`` is written into ``models/``, where
``app/llm_local.py`` picks it up automatically (it selects the largest ``*.gguf``
in that directory when the filename does not match the download default), so no
configuration change is needed after a successful run.


What the two llama.cpp tools actually do
----------------------------------------
``convert_hf_to_gguf.py`` (pure Python, ships with the llama.cpp repo) reads a
Hugging Face checkpoint — ``config.json``, the tokenizer files and the
``*.safetensors`` shards — and rewrites it as a single **GGUF** file. GGUF is
llama.cpp's container format: a header of key/value metadata (architecture,
rope parameters, tokeniser vocabulary and merges, chat template) followed by the
named weight tensors. ``--outtype f16`` keeps every weight at 16-bit, so this
step is a *format* change, not a compression step: quality is unchanged and the
file is roughly the same size as the original checkpoint. It exists because the
quantiser only understands GGUF.

``llama-quantize`` (a compiled C++ binary from the same repo) is the step that
actually shrinks the model. It rewrites each tensor into a block-quantised
format: weights are grouped into small blocks, and each block stores low-bit
integer codes plus a scale (and, for the "K-quant" families, a second-level
scale). ``Q4_K_M`` is the medium K-quant mix at ~4.5 bits per weight — most
tensors go to 4-bit, while the layers that hurt most under compression
(attention ``v`` projections and the feed-forward ``down`` projections in part
of the network, plus embeddings/output) are kept at 6-bit. That mix is why
Q4_K_M is the usual quality/size sweet spot: a 7B model drops from ~14 GB to
~4.4 GB — small enough for an 8-16 GB laptop — for a small, well-documented
perplexity increase.


Honest tradeoff (read this before quoting timings in the dissertation)
----------------------------------------------------------------------
There are two ways to get a Q4_K_M GGUF, and this project ships both on purpose:

*   ``app/setup_model.py`` (**the default, used by setup.bat**) downloads an
    already-quantised ~4.4 GB GGUF. It needs ~4.4 GB of disk and no build
    tools, and finishes in minutes. This is what a demo or a viva runs on.
*   ``app/quantize_model.py`` (**this file**) reproduces the quantisation
    locally. It needs a C++ toolchain (CMake + a compiler) to build
    ``llama-quantize``, ~14 GB of download, ~20 GB of free disk for the FP16
    checkpoint plus both GGUFs, and tens of minutes to hours depending on the
    machine.

Both produce the *same class* of artefact, and the running app cannot tell them
apart. The difference is provenance, not capability. The claim this project can
honestly make is: "the quantisation pipeline is implemented and reproducible
here, and the shipped default is a pre-quantised build of the same model at the
same bit-width, used so the application installs in minutes." Claiming the
demo binary was self-quantised when it was downloaded would be false — run this
script once, keep the log, and report which artefact each measurement used.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import Optional

from .setup_model import PROJECT_ROOT, models_dir

# Default FP16 source: same model as the pre-quantised fast path, so the two
# artefacts are directly comparable in the evaluation chapter.
DEFAULT_HF_REPO = "mistralai/Mistral-7B-Instruct-v0.2"
DEFAULT_QUANT = "Q4_K_M"
LLAMA_CPP_URL = "https://github.com/ggml-org/llama.cpp.git"

# Files we need from the HF checkpoint; excludes .bin duplicates of the
# safetensors shards and the consolidated single-file dumps, which would
# otherwise double the download.
HF_ALLOW_PATTERNS = ["*.safetensors", "*.json", "*.model", "*.txt"]
HF_IGNORE_PATTERNS = ["consolidated*", "*.pth", "original/*"]


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


# ---------------------------------------------------------------------------
# Step 0 — llama.cpp tooling
# ---------------------------------------------------------------------------
def llama_cpp_dir() -> str:
    """Where the llama.cpp source tree lives (``LLAMA_CPP_DIR`` overrides)."""
    configured = _env("LLAMA_CPP_DIR")
    if configured:
        return os.path.abspath(configured)
    return os.path.join(PROJECT_ROOT, "third_party", "llama.cpp")


def find_converter() -> Optional[str]:
    """Locate ``convert_hf_to_gguf.py`` (older trees name it convert-hf-to-gguf.py)."""
    root = llama_cpp_dir()
    for name in ("convert_hf_to_gguf.py", "convert-hf-to-gguf.py"):
        candidate = os.path.join(root, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def find_quantize_binary() -> Optional[str]:
    """Locate the compiled ``llama-quantize`` executable.

    Checks PATH first (package installs, Homebrew, winget), then the usual
    CMake output directories inside the source tree. ``quantize`` is the
    pre-2024 name and is accepted for older checkouts.
    """
    for name in ("llama-quantize", "quantize"):
        found = shutil.which(name)
        if found:
            return found

    root = llama_cpp_dir()
    exe = ".exe" if sys.platform.startswith("win") else ""
    search_dirs = [
        os.path.join(root, "build", "bin", "Release"),
        os.path.join(root, "build", "bin"),
        os.path.join(root, "build", "Release"),
        os.path.join(root, "build"),
        root,
    ]
    for directory in search_dirs:
        for name in ("llama-quantize", "quantize"):
            candidate = os.path.join(directory, name + exe)
            if os.path.isfile(candidate):
                return candidate
    return None


def ensure_llama_cpp(auto_clone: bool = True) -> str:
    """Make sure the llama.cpp source tree is present; clone it if allowed."""
    root = llama_cpp_dir()
    if find_converter():
        return root
    if not auto_clone:
        raise RuntimeError(
            f"llama.cpp not found at {root}. Clone it with:\n"
            f"    git clone --depth 1 {LLAMA_CPP_URL} \"{root}\"")
    if not shutil.which("git"):
        raise RuntimeError(
            "git is not installed, so llama.cpp cannot be fetched. Install git "
            f"or clone {LLAMA_CPP_URL} into {root} manually.")

    os.makedirs(os.path.dirname(root), exist_ok=True)
    print(f"[1/4] Cloning llama.cpp into {root} ...")
    _run(["git", "clone", "--depth", "1", LLAMA_CPP_URL, root])
    if not find_converter():
        raise RuntimeError(
            f"Cloned llama.cpp but convert_hf_to_gguf.py is missing in {root}.")
    return root


def build_hint() -> str:
    """Copy-pasteable instructions for building ``llama-quantize``."""
    root = llama_cpp_dir()
    return (
        "llama-quantize was not found. Build it once with CMake:\n"
        f"    cd \"{root}\"\n"
        "    cmake -B build\n"
        "    cmake --build build --config Release -j\n"
        "The binary lands in build/bin (build/bin/Release on Windows/MSVC).\n"
        "This needs a C++ compiler: Visual Studio Build Tools on Windows, "
        "build-essential on Linux, Xcode CLT on macOS.")


# ---------------------------------------------------------------------------
# Step 1 — download the FP16 checkpoint
# ---------------------------------------------------------------------------
def download_fp16(repo_id: str, dest_root: str) -> str:
    """Snapshot the full-precision HF checkpoint. Returns its local directory.

    Some upstream repos (notably Meta's Llama weights) are gated and require
    accepting a licence on the Hub; set ``HF_TOKEN`` in ``.env`` for those.
    """
    from huggingface_hub import snapshot_download  # lazy: optional dependency

    local_dir = os.path.join(dest_root, repo_id.replace("/", "__"))
    os.makedirs(local_dir, exist_ok=True)
    print(f"[2/4] Downloading FP16 weights for {repo_id}")
    print("      This is the full-precision checkpoint (~14 GB for a 7B model).")
    sys.stdout.flush()

    return snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        allow_patterns=HF_ALLOW_PATTERNS,
        ignore_patterns=HF_IGNORE_PATTERNS,
        token=_env("HF_TOKEN") or None,
    )


# ---------------------------------------------------------------------------
# Step 2 — HF -> GGUF FP16
# ---------------------------------------------------------------------------
def convert_to_gguf(hf_dir: str, out_path: str) -> str:
    """Run ``convert_hf_to_gguf.py`` to repackage the checkpoint as FP16 GGUF.

    Format conversion only: no weights are compressed here, so the output is
    about the same size as the input. ``llama-quantize`` does the compression.
    """
    converter = find_converter()
    if not converter:
        raise RuntimeError(f"convert_hf_to_gguf.py not found in {llama_cpp_dir()}")
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        print(f"[3/4] FP16 GGUF already exists, reusing: {out_path}")
        return out_path

    print(f"[3/4] Converting {hf_dir} -> {out_path} (GGUF, FP16)")
    _run([sys.executable, converter, hf_dir,
          "--outfile", out_path, "--outtype", "f16"])
    if not os.path.isfile(out_path):
        raise RuntimeError("Conversion finished but produced no output file.")
    return out_path


# ---------------------------------------------------------------------------
# Step 3 — GGUF FP16 -> GGUF Q4_K_M
# ---------------------------------------------------------------------------
def quantize_gguf(fp16_path: str, out_path: str,
                  quant_type: str = DEFAULT_QUANT) -> str:
    """Run ``llama-quantize`` to produce the low-bit GGUF.

    ``quant_type`` is a llama.cpp quantisation name: ``Q4_K_M`` (default,
    ~4.5 bits/weight), ``Q5_K_M`` (larger, closer to FP16), ``Q8_0`` (near
    lossless, ~2x the size of Q4), ``Q3_K_M`` (smaller, noticeably degraded).
    """
    binary = find_quantize_binary()
    if not binary:
        raise RuntimeError(build_hint())

    print(f"[4/4] Quantising -> {quant_type}")
    print(f"      {fp16_path}")
    print(f"   -> {out_path}")
    _run([binary, fp16_path, out_path, quant_type])
    if not os.path.isfile(out_path):
        raise RuntimeError("Quantisation finished but produced no output file.")
    return out_path


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _run(cmd: list) -> None:
    """Run a subprocess, streaming its output, raising on a non-zero exit."""
    print("      $ " + " ".join(f'"{c}"' if " " in str(c) else str(c)
                                for c in cmd))
    sys.stdout.flush()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {cmd[0]}")


def _size_gb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 ** 3)
    except OSError:
        return 0.0


def quantize(repo_id: str = DEFAULT_HF_REPO, quant_type: str = DEFAULT_QUANT,
             work_dir: Optional[str] = None, keep_fp16: bool = False,
             auto_clone: bool = True) -> str:
    """Run the whole FP16 -> Q4_K_M pipeline. Returns the final GGUF path."""
    work_dir = work_dir or os.path.join(PROJECT_ROOT, "models", "_work")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(models_dir(), exist_ok=True)

    slug = repo_id.split("/")[-1].lower()
    fp16_gguf = os.path.join(work_dir, f"{slug}.f16.gguf")
    final_gguf = os.path.join(models_dir(), f"{slug}.{quant_type}.gguf")

    if os.path.isfile(final_gguf):
        print(f"Already quantised: {final_gguf} ({_size_gb(final_gguf):.2f} GB)")
        return final_gguf

    ensure_llama_cpp(auto_clone=auto_clone)
    # Fail fast on the toolchain before spending 14 GB of bandwidth.
    if not find_quantize_binary():
        raise RuntimeError(build_hint())

    hf_dir = download_fp16(repo_id, work_dir)
    convert_to_gguf(hf_dir, fp16_gguf)
    quantize_gguf(fp16_gguf, final_gguf, quant_type)

    fp16_gb, final_gb = _size_gb(fp16_gguf), _size_gb(final_gguf)
    if not keep_fp16:
        try:
            os.remove(fp16_gguf)
        except OSError:
            pass

    print()
    print("  Quantisation complete")
    print(f"    source repo : {repo_id}")
    print(f"    FP16 GGUF   : {fp16_gb:.2f} GB"
          + ("" if keep_fp16 else "  (deleted; pass --keep-fp16 to retain)"))
    print(f"    {quant_type} GGUF : {final_gb:.2f} GB")
    if fp16_gb and final_gb:
        print(f"    compression : {fp16_gb / final_gb:.2f}x smaller "
              f"({100 * (1 - final_gb / fp16_gb):.1f}% reduction)")
    print(f"    output      : {final_gguf}")
    print("    app/llm_local.py will pick this up automatically.")
    print()
    return final_gguf


def _report_tooling() -> int:
    converter = find_converter()
    binary = find_quantize_binary()
    print()
    print("  Quantisation toolchain")
    print(f"    llama.cpp dir    : {llama_cpp_dir()}")
    print(f"    converter        : {converter or 'NOT FOUND (will be cloned)'}")
    print(f"    llama-quantize   : {binary or 'NOT FOUND'}")
    print(f"    output dir       : {models_dir()}")
    print()
    if not binary:
        print(build_hint())
        print()
    return 0 if (converter and binary) else 1


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.quantize_model",
        description="Quantise an FP16 Hugging Face model to GGUF Q4_K_M "
                    "using llama.cpp (the reproducible dissertation path).")
    parser.add_argument("--repo", default=DEFAULT_HF_REPO,
                        help=f"Hugging Face model id (default: {DEFAULT_HF_REPO})")
    parser.add_argument("--quant", default=DEFAULT_QUANT,
                        help=f"llama.cpp quant type (default: {DEFAULT_QUANT})")
    parser.add_argument("--work-dir",
                        help="scratch directory for the FP16 download/GGUF")
    parser.add_argument("--keep-fp16", action="store_true",
                        help="keep the intermediate FP16 GGUF")
    parser.add_argument("--no-clone", action="store_true",
                        help="do not auto-clone llama.cpp if it is missing")
    parser.add_argument("--check", action="store_true",
                        help="report toolchain status and exit")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    except Exception:
        pass

    if args.check:
        return _report_tooling()

    try:
        quantize(repo_id=args.repo, quant_type=args.quant,
                 work_dir=args.work_dir, keep_fp16=args.keep_fp16,
                 auto_clone=not args.no_clone)
    except Exception as exc:
        print()
        print(f"  [ERROR] Quantisation failed: {exc}")
        print("  The app is unaffected — it falls back to the pre-quantised "
              "download (python -m app.setup_model), then Groq, then rules.")
        print()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
