"""SQLite storage, schema and CRUD for NutriMind AI.

Tables
------
foods        - seeded IFCT-referenced food dataset (read-only at runtime)
users        - registered accounts (email + PBKDF2 password hash)
sessions     - opaque server-side session tokens -> user
profiles     - one biometric/preference profile per user (upserted)
food_prefs   - liked/disliked food-card keys per user (JSON)
goal_logs    - daily tracker entries (note + AI summary + 1-10 score)
reviews      - user feedback on features
meal_plans   - saved day-plan history (JSON)
recipes      - saved AI recipe history (JSON)

Design: keep all I/O here; nutrition.py stays pure. Connections are opened and
closed per call (SQLite handles this well for a single-node app).
"""
from __future__ import annotations
import json
import os
import sqlite3

from .foods import FOODS, COLUMNS
from .auth import new_session_token

_DEFAULT_DB = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "nutrimind.db"))
# Allow overriding the DB location (e.g. for sandboxed/network filesystems
# where SQLite file locking is unreliable). Falls back to the bundled data dir.
DB_PATH = os.environ.get("NUTRIMIND_DB", _DEFAULT_DB)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema + seeding
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT UNIQUE NOT NULL,
    region    TEXT NOT NULL,
    diet      TEXT NOT NULL,
    meal_slot TEXT NOT NULL,
    serving_g REAL NOT NULL,
    kcal      REAL NOT NULL,
    protein_g REAL NOT NULL,
    carb_g    REAL NOT NULL,
    fat_g     REAL NOT NULL,
    fibre_g   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token   TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    dob             TEXT,
    age             INTEGER,
    sex             TEXT,
    height_cm       REAL,
    weight_kg       REAL,
    activity        TEXT,
    goal            TEXT,
    diet            TEXT,
    region          TEXT,
    allergies       TEXT,
    bmi             REAL,
    bmi_category    TEXT,
    target_calories INTEGER,
    updated         TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS food_prefs (
    user_id  INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    liked    TEXT DEFAULT '[]',
    disliked TEXT DEFAULT '[]',
    updated  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goal_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date       TEXT NOT NULL,
    note_text      TEXT NOT NULL,
    ai_summary     TEXT,
    activity_score INTEGER,
    weight_kg      REAL,
    created        TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feature TEXT,
    rating  INTEGER,
    comment TEXT,
    created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meal_plans (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_json TEXT NOT NULL,
    created   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dish        TEXT NOT NULL,
    servings    INTEGER,
    recipe_json TEXT NOT NULL,
    created     TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(force: bool = False) -> int:
    """Create all tables and seed foods. Returns number of foods seeded."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(_SCHEMA)

    cur.execute("SELECT COUNT(*) AS c FROM foods")
    have = cur.fetchone()["c"]
    # Self-healing: (re)seed whenever the table is empty, incomplete (e.g. a
    # partial DB left by an interrupted first run), or when force is requested.
    if force or have != len(FOODS):
        cur.execute("DELETE FROM foods")
        placeholders = ",".join(["?"] * len(COLUMNS))
        cur.executemany(
            f"INSERT INTO foods ({','.join(COLUMNS)}) VALUES ({placeholders})",
            FOODS,
        )

    conn.commit()
    cur.execute("SELECT COUNT(*) AS c FROM foods")
    n = cur.fetchone()["c"]
    conn.close()
    return n


# ---------------------------------------------------------------------------
# Foods
# ---------------------------------------------------------------------------
def query_foods(region: str | None = None, diet: str | None = None,
                meal_slot: str | None = None) -> list[dict]:
    """Fetch foods, optionally filtered. Region match includes Pan-India.

    Diet filter is inclusive: vegan ⊂ veg request, etc.
        - 'veg' user accepts: veg, vegan
        - 'vegan' user accepts: vegan only
        - 'nonveg' user accepts: everything
    """
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM foods WHERE 1=1"
    params: list = []

    if region and region != "Pan-India":
        sql += " AND (region = ? OR region = 'Pan-India')"
        params.append(region)

    if diet == "veg":
        sql += " AND diet IN ('veg','vegan')"
    elif diet == "vegan":
        sql += " AND diet = 'vegan'"
    # nonveg: no filter (accepts all)

    if meal_slot:
        sql += " AND meal_slot = ?"
        params.append(meal_slot)

    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Users + sessions
# ---------------------------------------------------------------------------
def create_user(name: str, email: str, salt: str, pwd_hash: str) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name,email,password_salt,password_hash) "
            "VALUES (?,?,?,?)",
            (name, email.lower().strip(), salt, pwd_hash),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(user_id: int) -> str:
    token = new_session_token()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO sessions (token,user_id) VALUES (?,?)",
                (token, user_id))
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: str) -> dict | None:
    if not token:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id "
        "WHERE s.token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------
_PROFILE_FIELDS = ("dob", "age", "sex", "height_cm", "weight_kg", "activity",
                   "goal", "diet", "region", "allergies", "bmi",
                   "bmi_category", "target_calories")


def upsert_profile(user_id: int, data: dict) -> None:
    """Insert or replace the user's single profile row."""
    vals = [data.get(f) for f in _PROFILE_FIELDS]
    cols = ",".join(_PROFILE_FIELDS)
    placeholders = ",".join(["?"] * len(_PROFILE_FIELDS))
    updates = ",".join(f"{f}=excluded.{f}" for f in _PROFILE_FIELDS)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO profiles (user_id,{cols},updated) "
        f"VALUES (?,{placeholders},CURRENT_TIMESTAMP) "
        f"ON CONFLICT(user_id) DO UPDATE SET {updates},updated=CURRENT_TIMESTAMP",
        [user_id, *vals],
    )
    conn.commit()
    conn.close()


def get_profile(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Food preferences
# ---------------------------------------------------------------------------
def upsert_prefs(user_id: int, liked: list[str], disliked: list[str]) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO food_prefs (user_id,liked,disliked,updated) "
        "VALUES (?,?,?,CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET liked=excluded.liked,"
        "disliked=excluded.disliked,updated=CURRENT_TIMESTAMP",
        (user_id, json.dumps(liked or []), json.dumps(disliked or [])),
    )
    conn.commit()
    conn.close()


def get_prefs(user_id: int) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT liked,disliked FROM food_prefs WHERE user_id = ?",
                (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"liked": [], "disliked": []}
    return {"liked": json.loads(row["liked"]),
            "disliked": json.loads(row["disliked"])}


# ---------------------------------------------------------------------------
# Goal tracker logs
# ---------------------------------------------------------------------------
def add_log(user_id: int, log_date: str, note_text: str, ai_summary: str,
            activity_score: int, weight_kg: float | None) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO goal_logs "
        "(user_id,log_date,note_text,ai_summary,activity_score,weight_kg) "
        "VALUES (?,?,?,?,?,?)",
        (user_id, log_date, note_text, ai_summary, activity_score, weight_kg),
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def list_logs(user_id: int, limit: int = 60) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM goal_logs WHERE user_id = ? "
        "ORDER BY log_date DESC, id DESC LIMIT ?", (user_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def log_stats(user_id: int) -> dict:
    """Aggregate tracker stats for the dashboard."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS n, AVG(activity_score) AS avg_score "
        "FROM goal_logs WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    cur.execute(
        "SELECT log_date, activity_score FROM goal_logs WHERE user_id = ? "
        "ORDER BY log_date DESC, id DESC LIMIT 14", (user_id,))
    recent = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "count": row["n"] or 0,
        "avg_score": round(row["avg_score"], 1) if row["avg_score"] else 0,
        "recent": list(reversed(recent)),
    }


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
def add_review(user_id: int, feature: str, rating: int, comment: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reviews (user_id,feature,rating,comment) VALUES (?,?,?,?)",
        (user_id, feature, rating, comment),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def list_reviews(limit: int = 30) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT r.feature,r.rating,r.comment,r.created,u.name "
        "FROM reviews r JOIN users u ON u.id = r.user_id "
        "ORDER BY r.id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# History (saved plans & recipes)
# ---------------------------------------------------------------------------
def save_meal_plan(user_id: int, plan: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO meal_plans (user_id,plan_json) VALUES (?,?)",
                (user_id, json.dumps(plan)))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def save_recipe(user_id: int, dish: str, servings: int, recipe: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recipes (user_id,dish,servings,recipe_json) "
        "VALUES (?,?,?,?)", (user_id, dish, servings, json.dumps(recipe)))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def list_recipes(user_id: int, limit: int = 10) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id,dish,servings,recipe_json,created FROM recipes "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["recipe"] = json.loads(d.pop("recipe_json"))
        rows.append(d)
    conn.close()
    return rows
