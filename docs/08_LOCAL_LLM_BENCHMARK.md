# Local Quantised LLM — Measured Results

Measured on the development machine, not estimated. These are the numbers the
final report should cite.

## Environment

| Item | Value |
|---|---|
| Model | Mistral-7B-Instruct-v0.2 |
| Quantisation | Q4_K_M (4-bit) |
| File size on disk | 4.07 GB (4,368,439,584 bytes) |
| Runtime | llama-cpp-python 0.3.34, CPU only (`GPU_LAYERS=0`) |
| Host RAM | 15.7 GB (auto-selected the 7B tier; <8 GB would select ~2.4 GB Phi-3-mini) |
| Backend setting | `NUTRIMIND_AI_BACKEND=local` |

## Latency

| Operation | Cold (includes model load) | Warm |
|---|---|---|
| Tracker log summary | 68.0 s | 31.8 s |
| Goal suggestion | — | 38.8 s |
| Recipe generation | — | 266.6 s |

Model load accounts for roughly 36 s of the cold figure. Recipe generation is
far slower than the other two because it emits a much longer structured
response (16 ingredients + 10 method steps) rather than a few short fields.

## Output quality

Structured output parsed correctly on every call — the model returned valid
typed fields, not free text needing repair.

- **Log summary** — input *"Morning 5k run, ate idli and sambar for breakfast,
  skipped fried snacks, drank 3L water."* → summary *"Completed 5k run in the
  morning, consumed a nutritious breakfast of idli and sambar, avoided fried
  snacks, and drank ample water."*, activity score 9/10.
- **Goal suggestion** — BMI 26.4 (Overweight) → `lose`, matching the clinical
  rule-based expectation.
- **Recipe** — *"paneer butter masala"*, 2 servings, veg, 760 kcal/serving
  budget → title *"Paneer Butter Masala (Veg, 2 Servings, About 760 kcal)"*,
  16 quantified ingredients, 10 method steps, first ingredient
  *"250 g paneer (cubed)"*.

## Interpretation

Local inference is **functionally correct but not interactive** on CPU. A ~30 s
wait for a log summary is tolerable; a ~4.5 min wait for a recipe is not, for a
live demonstration.

Practical consequences:

1. `NUTRIMIND_AI_BACKEND=auto` (the default) is the right setting for a demo —
   Groq answers in about a second, and the local tier exists as the offline,
   zero-cost, privacy-preserving path.
2. `NUTRIMIND_AI_BACKEND=local` is what demonstrates the dissertation's claim:
   the whole system running with no network and no API key.
3. The latency is dominated by CPU-only decoding. Offloading layers to a GPU
   (`LOCAL_MODEL_GPU_LAYERS`) or selecting the smaller Phi-3-mini build would
   both reduce it substantially; neither has been measured yet.

## Not yet measured

- Tokens/second decode rate (only wall-clock per operation was recorded).
- The smaller ~2.4 GB Phi-3-mini build on a low-RAM machine.
- GPU-offloaded latency.
- Output-quality comparison against the Groq baseline on a fixed prompt set.
