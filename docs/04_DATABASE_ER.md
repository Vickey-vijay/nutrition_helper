# NutriMind AI — Database Design (ER Diagram)

SQLite schema. One `users` row owns one `profiles` row and one `food_prefs` row,
and many `sessions`, `goal_logs`, `reviews`, `meal_plans` and `recipes`. The `foods`
table is a seeded, read-only reference set (IFCT 2017).

```mermaid
erDiagram
    USERS ||--o| PROFILES     : has
    USERS ||--o| FOOD_PREFS    : has
    USERS ||--o{ SESSIONS      : owns
    USERS ||--o{ GOAL_LOGS     : records
    USERS ||--o{ REVIEWS       : writes
    USERS ||--o{ MEAL_PLANS    : saves
    USERS ||--o{ RECIPES       : saves
    FOODS }o..o{ MEAL_PLANS    : "referenced by (by name)"

    USERS {
        int     id PK
        text    name
        text    email UK
        text    password_salt
        text    password_hash
        text    created
    }
    SESSIONS {
        text    token PK
        int     user_id FK
        text    created
    }
    PROFILES {
        int     user_id PK_FK
        text    dob
        int     age
        text    sex
        real    height_cm
        real    weight_kg
        text    activity
        text    goal
        text    diet
        text    region
        text    allergies
        real    bmi
        text    bmi_category
        int     target_calories
        text    updated
    }
    FOOD_PREFS {
        int     user_id PK_FK
        text    liked "JSON array of card keys"
        text    disliked "JSON array of card keys"
        text    updated
    }
    GOAL_LOGS {
        int     id PK
        int     user_id FK
        text    log_date
        text    note_text
        text    ai_summary
        int     activity_score "1-10"
        real    weight_kg
        text    created
    }
    REVIEWS {
        int     id PK
        int     user_id FK
        text    feature
        int     rating "1-5"
        text    comment
        text    created
    }
    MEAL_PLANS {
        int     id PK
        int     user_id FK
        text    plan_json
        text    created
    }
    RECIPES {
        int     id PK
        int     user_id FK
        text    dish
        int     servings
        text    recipe_json
        text    created
    }
    FOODS {
        int     id PK
        text    name UK
        text    region
        text    diet
        text    meal_slot
        real    serving_g
        real    kcal "per 100g"
        real    protein_g
        real    carb_g
        real    fat_g
        real    fibre_g
    }
```

## Notes

- **Referential integrity:** `PRAGMA foreign_keys = ON`; child rows cascade-delete
  with their user.
- **One-to-one tables** (`profiles`, `food_prefs`) use `user_id` as the primary key
  and are written with `INSERT … ON CONFLICT(user_id) DO UPDATE` (upsert).
- **JSON columns:** preference card keys are stored as JSON text arrays — flexible
  without extra tables.
- **`foods`** is idempotently seeded on startup and self-heals if the row count
  drifts from the source dataset.
- **Security:** passwords are never stored in plaintext — only a random
  `password_salt` and the PBKDF2 `password_hash`.
