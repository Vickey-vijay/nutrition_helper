# CLAUDE.md — NutriMind AI

Guidance for AI assistants working in this repository.

## What this is

A region-aware, AI-assisted personalised diet-planning platform for Indian users
(BITS Pilani dissertation). FastAPI + SQLite + a vanilla-JS SPA. 100% free to run.
Accounts, profiles, preference-driven meal plans, an AI recipe generator, a goal
tracker and reviews.

## Architecture

- `app/nutrition.py` — pure functions: BMI (WHO), BMR (Mifflin-St Jeor), TDEE
  (Harris-Benedict), goal-adjusted target calories, `age_from_dob`. No I/O.
- `app/foods.py` — seed food dataset (`FOODS`, per-100g macros, IFCT 2017) plus
  `FOOD_CARDS` (preference categories) and `keywords_for()`.
- `app/database.py` — SQLite schema + CRUD for users, sessions, profiles,
  food_prefs, goal_logs, reviews, meal_plans, recipes, foods. All I/O lives here.
- `app/auth.py` — PBKDF2 password hashing + opaque session tokens (stdlib only).
- `app/mealplan.py` — `build_day_plan(region, diet, target, seed, prefs)`; filters
  disliked foods, prefers liked ones, normalises portions to the calorie target.
- `app/ai.py` — LangChain + Groq layer: `meal_guidance`, `suggest_goal`,
  `generate_recipe`, `summarize_log`. Structured outputs via Pydantic. Deterministic
  rule-based fallback when `GROQ_API_KEY` is unset or a call fails.
- `app/main.py` — FastAPI routes; `current_user` Bearer-token dependency; serves
  `frontend/`.
- `frontend/` — `index.html` + `app.js` (SPA controller) + `styles.css`.
- `docs/` — project plan, architecture, ER/class/sequence diagrams (Mermaid),
  quantisation roadmap.

## Core design rule

**The LLM never produces nutrition numbers.** All calories/macros come from the
IFCT-referenced database and `nutrition.py`. The LLM writes recipe/guidance *text*
only. For recipes, the per-serving calorie *budget* is Python-derived; the model's
own kcal figure is shown separately as an "approx" estimate. Preserve this
separation when extending the AI layer.

## Conventions

- Diet inclusivity: `veg` includes `vegan`; `nonveg` includes all; `vegan` is strict.
- Region queries always include `Pan-India` staples as fallbacks.
- Keep `nutrition.py` pure and unit-testable; put I/O in `database.py`.
- The AI provider is isolated in `ai.py` — swapping Groq for a local quantised model
  (final sem) is a one-file change. Keep the fallback intact.
- No paid dependencies. The app must run with zero API keys configured.
- Secrets live in `.env` (gitignored); never commit keys.

## Run / test

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
python -m app.selftest        # 13 end-to-end checks against a running server
```

Windows one-click: `start.bat` (installs + launches).
