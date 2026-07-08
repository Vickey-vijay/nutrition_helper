# NutriMind AI — Sequence Diagrams

## 1. Registration & login

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend (app.js)
    participant API as FastAPI
    participant AU as auth.py
    participant DB as SQLite

    U->>FE: submit register form
    FE->>API: POST /api/auth/register {name,email,password}
    API->>DB: get_user_by_email(email)
    DB-->>API: none (ok) / exists → 409
    API->>AU: hash_password(password)
    AU-->>API: (salt, hash)
    API->>DB: create_user(...)
    API->>DB: create_session(user_id)
    DB-->>API: token
    API-->>FE: { token, user }
    FE->>FE: localStorage.setItem(token)
    FE->>API: GET /api/me (Bearer token)
    API-->>FE: { user, profile, prefs, tracker }
    FE-->>U: Dashboard
```

## 2. AI meal plan (numbers from DB, text from LLM)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as FastAPI
    participant N as nutrition.py
    participant M as mealplan.py
    participant DB as SQLite
    participant AI as ai.py (LangChain)
    participant G as Groq LLM

    U->>FE: click "Generate plan"
    FE->>API: POST /api/plan (Bearer)
    API->>DB: get_profile / get_prefs
    API->>N: full_profile_metrics(profile)
    N-->>API: {bmi, bmr, tdee, target_calories}
    API->>M: build_day_plan(region, diet, target, prefs)
    M->>DB: query_foods(region, diet)
    M-->>API: plan (portions + macros from IFCT)
    API->>AI: meal_guidance(plan, metrics, prefs)
    alt GROQ_API_KEY set
        AI->>G: prompt (meal names only, no numbers)
        G-->>AI: guidance text
    else no key / error
        AI->>AI: rule-based fallback text
    end
    AI-->>API: {source, guidance}
    API->>DB: save_meal_plan(history)
    API-->>FE: {metrics, plan, guidance}
    FE-->>U: table + AI guidance
```

## 3. AI recipe — structured output, scaled to the user

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as FastAPI
    participant N as nutrition.py
    participant AI as ai.py
    participant G as Groq (structured output)
    participant DB as SQLite

    U->>FE: type dish + servings, Generate
    FE->>API: POST /api/recipe {dish, servings}
    API->>DB: get_profile
    API->>N: full_profile_metrics → target_calories
    API->>API: budget = round(target * 0.35)  %% Python-derived
    API->>AI: generate_recipe(dish, servings, diet, budget)
    AI->>G: ChatGroq.with_structured_output(RecipeOut)
    G-->>AI: {title, ingredients, steps, health_notes, approx_kcal, prep_time}
    AI-->>API: recipe (+ budget_kcal_per_serving)
    API->>DB: save_recipe(history)
    API-->>FE: recipe
    FE-->>U: budget (your body) vs AI estimate, ingredients, steps
```

## 4. Goal tracker — AI day scoring

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as FastAPI
    participant AI as ai.py
    participant G as Groq (structured output)
    participant DB as SQLite

    U->>FE: write daily note (+ optional weight)
    FE->>API: POST /api/log {note_text, weight_kg}
    API->>AI: summarize_log(note_text)
    AI->>G: with_structured_output(LogOut)
    G-->>AI: {summary, activity_score 1-10, encouragement}
    AI-->>API: scored summary
    API->>DB: add_log(...)
    API->>DB: log_stats(user)
    API-->>FE: {ai, stats}
    FE-->>U: summary + score + updated trend bars
```
