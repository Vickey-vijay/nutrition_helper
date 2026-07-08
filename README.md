# 🌿 NutriMind AI

A **region-aware, AI-assisted personalised diet-planning platform for Indian users**.
Create an account, save your biometrics, and get a clinically-grounded calorie target,
a day's meal plan built from foods local to your region of India, an AI recipe
generator, and a goal tracker that scores your day — all **100% free to run**.

> BITS Pilani dissertation project. Nutrition values are referenced against the
> **Indian Food Composition Tables (IFCT 2017, NIN/ICMR)**.

> 📋 **New here / non-technical setup?** See [`SETUP_GUIDE.md`](SETUP_GUIDE.md)
> for a plain, step-by-step install guide (download ZIP → `setup.bat` → `run.bat`).

---

## ✨ Features

- **User accounts** — register / login with securely hashed passwords (PBKDF2) and
  server-side session tokens. Your data stays in a local SQLite file.
- **Clinical nutrition engine** — WHO BMI, **Mifflin-St Jeor** BMR, Harris-Benedict
  TDEE, and a goal-adjusted daily calorie target.
- **🤖 AI goal suggestion** — the AI recommends *lose / maintain / gain* from your
  biometrics, so you don't have to self-diagnose.
- **Region-aware meal plans** — breakfast/lunch/dinner/snack assembled from 50+
  region-tagged Indian foods, scaled to your target (typically ±10%).
- **Food preferences** — tap-to-pick like/avoid cards that bias your meal plans.
- **Healthy recipe generator** — type any dish; the AI returns its healthiest
  version, scaled to your body's per-serving calorie budget and serving count.
- **Goal tracker** — write a daily note; the AI summarises it and scores your day
  1–10, with a running activity-trend chart.
- **Reviews** — rate features and leave feedback.
- **Always works** — the AI layer (LangChain + Groq) degrades to a deterministic
  rule-based fallback when no API key is set, so the app runs with **zero setup**.

> **Design guarantee:** the LLM only writes *text* (tips, recipes, summaries). Every
> calorie/macro **number** comes from the IFCT-referenced database — never the model.

## 🧱 Tech stack

| Layer    | Choice                                   |
|----------|------------------------------------------|
| Backend  | Python · FastAPI · Uvicorn               |
| Storage  | SQLite (seeded on startup)               |
| Auth     | PBKDF2-HMAC-SHA256 + token sessions      |
| AI       | LangChain + Groq (Llama 3.3) + fallback  |
| Frontend | Plain HTML/CSS/JS (no build step)        |

## 🚀 Quick start (Windows — one click)

1. Double-click **`start.bat`** — it creates the virtual environment, installs
   dependencies, and launches the app at <http://localhost:8000>.

That's it. (First run takes a minute to install; later runs are instant.)

### Optional: enable the live AI

The app works without a key (rule-based fallback). To enable the Groq LLM, open
`.env` and set your free key from <https://console.groq.com>:

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```

### Manual start (any OS)

```bash
cd nutrimind
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional: add GROQ_API_KEY
uvicorn app.main:app --port 8000
```

## 🔌 API

| Method | Path                 | Auth | Purpose                                  |
|--------|----------------------|------|------------------------------------------|
| GET    | `/api/health`        | —    | Liveness, food count, active AI mode     |
| POST   | `/api/auth/register` | —    | Create an account                        |
| POST   | `/api/auth/login`    | —    | Sign in (returns a session token)        |
| POST   | `/api/auth/logout`   | ✓    | Invalidate the session                   |
| GET    | `/api/me`            | ✓    | User + profile + prefs + tracker stats   |
| POST   | `/api/profile`       | ✓    | Save biometrics → BMI + calorie target   |
| POST   | `/api/suggest-goal`  | ✓    | AI goal recommendation                   |
| GET    | `/api/food-cards`    | —    | Food-preference card catalogue           |
| GET/POST | `/api/preferences` | ✓    | Read / save liked & avoided foods        |
| POST   | `/api/plan`          | ✓    | Day meal plan + AI guidance              |
| POST   | `/api/recipe`        | ✓    | AI recipe scaled to the user             |
| GET    | `/api/recipes`       | ✓    | Recipe history                           |
| POST   | `/api/log`           | ✓    | Add tracker note → AI summary + score    |
| GET    | `/api/logs`          | ✓    | Tracker history + stats                  |
| POST/GET | `/api/review(s)`   | ✓    | Submit / list reviews                    |

Authenticated calls send `Authorization: Bearer <token>`.

## 🧪 Test

```bash
uvicorn app.main:app --port 8000      # in one terminal
python -m app.selftest                 # in another — runs 13 end-to-end checks
```

## 🗂️ Project layout

```
nutrimind/
├── app/
│   ├── main.py        # FastAPI routes + auth dependency
│   ├── auth.py        # password hashing + session tokens
│   ├── nutrition.py   # BMI / BMR / TDEE / target (pure functions)
│   ├── foods.py       # IFCT-referenced foods + preference cards
│   ├── database.py    # SQLite schema, seeding, CRUD
│   ├── mealplan.py    # preference-aware day-plan builder
│   ├── ai.py          # LangChain + Groq layer + rule-based fallback
│   └── selftest.py    # end-to-end API smoke test
├── frontend/          # index.html · app.js · styles.css (SPA)
├── docs/              # plan, architecture & diagrams (Mermaid)
├── data/nutrimind.db  # created on first run
├── setup.bat · run.bat · start.bat
├── .env.example
└── requirements.txt
```

See [`docs/`](docs/) for the full project plan, architecture, ER/class/sequence
diagrams, and the final-semester local-quantised-LLM roadmap.
