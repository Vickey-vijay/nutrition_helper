# NutriMind AI — Module & Class Diagram

Python is organised as cohesive modules (pure functions + Pydantic schemas) rather
than a deep class hierarchy. The diagram below shows the request schemas, the AI
structured-output models, and the functional contracts of each module.

## 1. Pydantic schemas & AI models

```mermaid
classDiagram
    class RegisterIn {
        +str name
        +EmailStr email
        +str password
    }
    class LoginIn {
        +EmailStr email
        +str password
    }
    class ProfileIn {
        +str dob
        +int age
        +str sex
        +float height_cm
        +float weight_kg
        +str activity
        +str goal
        +str diet
        +str region
        +str allergies
    }
    class PrefsIn {
        +list~str~ liked
        +list~str~ disliked
    }
    class RecipeIn {
        +str dish
        +int servings
    }
    class LogIn {
        +str note_text
        +str log_date
        +float weight_kg
    }
    class ReviewIn {
        +str feature
        +int rating
        +str comment
    }

    class GoalOut {
        +str goal
        +str rationale
    }
    class RecipeOut {
        +str title
        +int servings
        +list~str~ ingredients
        +list~str~ steps
        +list~str~ health_notes
        +int approx_calories_per_serving
        +int prep_time_min
    }
    class LogOut {
        +str summary
        +int activity_score
        +str encouragement
    }
```

## 2. Module contracts

```mermaid
classDiagram
    class nutrition {
        <<pure functions>>
        +age_from_dob(dob) int
        +compute_bmi(w, h) float
        +classify_bmi(bmi) str
        +compute_bmr(w, h, age, sex) float
        +compute_tdee(bmr, activity) float
        +compute_target_calories(tdee, goal) int
        +full_profile_metrics(...) dict
    }
    class foods {
        +FOODS : list
        +FOOD_CARDS : list
        +keywords_for(keys) list
    }
    class database {
        +init_db() int
        +query_foods(region, diet, slot) list
        +create_user(...) int
        +get_user_by_token(token) dict
        +create_session(uid) str
        +upsert_profile(uid, data)
        +get_profile(uid) dict
        +upsert_prefs(uid, liked, disliked)
        +add_log(...) int
        +log_stats(uid) dict
        +add_review(...) int
        +save_meal_plan(uid, plan) int
        +save_recipe(...) int
    }
    class auth {
        +hash_password(pw) tuple
        +verify_password(pw, salt, hash) bool
        +new_session_token() str
    }
    class mealplan {
        +build_day_plan(region, diet, target, seed, prefs) dict
    }
    class ai {
        +ai_mode() str
        +meal_guidance(plan, metrics, prefs) dict
        +suggest_goal(metrics) dict
        +generate_recipe(dish, metrics, servings, diet, budget) dict
        +summarize_log(note) dict
    }
    class main {
        <<FastAPI app>>
        +current_user(authorization) dict
        +register() ; login() ; logout()
        +save_profile() ; suggest_goal()
        +plan() ; preferences()
        +recipe() ; add_log() ; add_review()
    }

    main ..> nutrition : uses
    main ..> mealplan : uses
    main ..> ai : uses
    main ..> database : uses
    main ..> auth : (via database)
    mealplan ..> database : query_foods
    mealplan ..> foods : keywords_for
    database ..> foods : seed data
    database ..> auth : new_session_token
    ai ..> GoalOut
    ai ..> RecipeOut
    ai ..> LogOut
```

## 3. Design principles applied

- **Single responsibility:** I/O isolated in `database.py`; math isolated in
  `nutrition.py` (pure, unit-testable).
- **Dependency direction:** `main` depends on services; services depend on
  `database`; nothing depends on `main`.
- **Provider abstraction:** `ai.py` is the only module that knows about the LLM —
  swapping Groq for a local model touches one file.
- **Schema-first validation:** every endpoint input is a Pydantic model; invalid
  requests are rejected with 422 before any handler logic runs.
