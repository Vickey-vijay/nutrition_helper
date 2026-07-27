"""NutriMind AI — FastAPI backend.

A region-aware, AI-assisted Indian diet-planning platform with user accounts,
profiles, preference-driven meal plans, an AI recipe generator, a goal tracker
and feedback capture. The AI layer (LangChain + Groq) writes guidance TEXT only;
all calorie/macro numbers come from the IFCT-referenced database.
"""
from __future__ import annotations
import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr

from . import database as db
from . import auth
from . import ai
from .foods import FOOD_CARDS
from .nutrition import (full_profile_metrics, age_from_dob,
                        ACTIVITY_MULTIPLIERS, ACTIVITY_LABELS, GOAL_ADJUSTMENTS)
from .mealplan import build_day_plan

app = FastAPI(title="NutriMind AI", version="2.0.0")

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend"))

FOOD_COUNT = 0


@app.on_event("startup")
def _startup():
    global FOOD_COUNT
    FOOD_COUNT = db.init_db()


# ===========================================================================
# Schemas
# ===========================================================================
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    dob: Optional[str] = None             # YYYY-MM-DD
    age: Optional[int] = Field(default=None, ge=10, le=100)
    sex: str
    height_cm: float = Field(gt=80, lt=250)
    weight_kg: float = Field(gt=20, lt=300)
    activity: str = "moderate"
    goal: str = "maintain"
    diet: str = "veg"
    region: str = "Pan-India"
    allergies: Optional[str] = None


class PrefsIn(BaseModel):
    liked: list[str] = []
    disliked: list[str] = []


class RecipeIn(BaseModel):
    dish: str = Field(min_length=2, max_length=120)
    servings: int = Field(default=1, ge=1, le=12)


class LogIn(BaseModel):
    note_text: str = Field(min_length=1, max_length=2000)
    log_date: Optional[str] = None
    weight_kg: Optional[float] = Field(default=None, gt=20, lt=300)


class ReviewIn(BaseModel):
    feature: str = Field(max_length=60)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class PlanIn(BaseModel):
    seed: Optional[int] = None


# ===========================================================================
# Auth dependency
# ===========================================================================
def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


def _public_user(user: dict) -> dict:
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


def _metrics_from_profile(p: dict) -> dict:
    return full_profile_metrics(p["age"], p["sex"], p["height_cm"],
                                p["weight_kg"], p["activity"], p["goal"])


# ===========================================================================
# Health & reference data
# ===========================================================================
@app.get("/api/health")
def health():
    ai_state = ai.ai_status()
    return {
        "status": "ok",
        "foods": FOOD_COUNT or db.init_db(),
        "ai_mode": ai_state["tier"],
        # Which of the three tiers (local quantised / groq cloud / rules) is
        # actually serving requests, plus the full chain diagnostics.
        "ai_tier": ai_state["tier"],
        "ai_last_tier": ai_state["last_tier"],
        "ai": ai_state,
        "model": ai_state["model"],
        "activity_levels": ACTIVITY_LABELS,
        "goals": list(GOAL_ADJUSTMENTS.keys()),
    }


@app.get("/api/foods")
def foods(region: Optional[str] = None, diet: Optional[str] = None,
          meal_slot: Optional[str] = None):
    rows = db.query_foods(region=region, diet=diet, meal_slot=meal_slot)
    return {"count": len(rows), "foods": rows}


@app.get("/api/food-cards")
def food_cards():
    return {"cards": FOOD_CARDS}


# ===========================================================================
# Authentication
# ===========================================================================
@app.post("/api/auth/register")
def register(body: RegisterIn):
    if db.get_user_by_email(body.email):
        raise HTTPException(409, "An account with this email already exists")
    salt, pwd_hash = auth.hash_password(body.password)
    uid = db.create_user(body.name.strip(), body.email, salt, pwd_hash)
    token = db.create_session(uid)
    return {"token": token, "user": _public_user(db.get_user_by_id(uid))}


@app.post("/api/auth/login")
def login(body: LoginIn):
    user = db.get_user_by_email(body.email)
    if not user or not auth.verify_password(
            body.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = db.create_session(user["id"])
    return {"token": token, "user": _public_user(user)}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        db.delete_session(authorization[7:].strip())
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    profile = db.get_profile(user["id"])
    metrics = _metrics_from_profile(profile) if profile else None
    return {
        "user": _public_user(user),
        "profile": profile,
        "metrics": metrics,
        "prefs": db.get_prefs(user["id"]),
        "tracker": db.log_stats(user["id"]),
    }


# ===========================================================================
# Profile
# ===========================================================================
@app.post("/api/profile")
def save_profile(body: ProfileIn, user: dict = Depends(current_user)):
    age = body.age
    if body.dob:
        try:
            age = age_from_dob(body.dob)
        except ValueError as e:
            raise HTTPException(422, str(e))
    if not age:
        raise HTTPException(422, "Provide either age or a valid date of birth")

    metrics = full_profile_metrics(age, body.sex, body.height_cm,
                                   body.weight_kg, body.activity, body.goal)
    record = {
        "dob": body.dob, "age": age, "sex": body.sex,
        "height_cm": body.height_cm, "weight_kg": body.weight_kg,
        "activity": body.activity, "goal": body.goal, "diet": body.diet,
        "region": body.region, "allergies": body.allergies,
        "bmi": metrics["bmi"], "bmi_category": metrics["bmi_category"],
        "target_calories": metrics["target_calories"],
    }
    db.upsert_profile(user["id"], record)
    return {"profile": db.get_profile(user["id"]), "metrics": metrics}


@app.post("/api/suggest-goal")
def suggest_goal(user: dict = Depends(current_user)):
    profile = db.get_profile(user["id"])
    if not profile:
        raise HTTPException(400, "Save your profile first")
    metrics = _metrics_from_profile(profile)
    return {"metrics": metrics, "suggestion": ai.suggest_goal(metrics)}


# ===========================================================================
# Meal plan (+ guidance)
# ===========================================================================
@app.post("/api/plan")
def plan(body: PlanIn = PlanIn(), user: dict = Depends(current_user)):
    profile = db.get_profile(user["id"])
    if not profile:
        raise HTTPException(400, "Save your profile first")
    metrics = _metrics_from_profile(profile)
    prefs = db.get_prefs(user["id"])
    day = build_day_plan(profile["region"], profile["diet"],
                         metrics["target_calories"], seed=body.seed, prefs=prefs)
    if not day["meals"]:
        raise HTTPException(404, "No foods matched this region/diet combination")
    guidance = ai.meal_guidance(day, metrics, prefs)
    saved_id = db.save_meal_plan(user["id"], day)
    return {"metrics": metrics, "plan": day, "guidance": guidance,
            "saved_id": saved_id}


# ===========================================================================
# Food preferences
# ===========================================================================
@app.get("/api/preferences")
def get_preferences(user: dict = Depends(current_user)):
    return db.get_prefs(user["id"])


@app.post("/api/preferences")
def set_preferences(body: PrefsIn, user: dict = Depends(current_user)):
    db.upsert_prefs(user["id"], body.liked, body.disliked)
    return {"ok": True, "prefs": db.get_prefs(user["id"])}


# ===========================================================================
# Recipe generator
# ===========================================================================
@app.post("/api/recipe")
def recipe(body: RecipeIn, user: dict = Depends(current_user)):
    profile = db.get_profile(user["id"])
    if not profile:
        raise HTTPException(400, "Save your profile first")
    metrics = _metrics_from_profile(profile)
    # Per-serving calorie budget for a main meal (~35% of the daily target).
    budget = round(metrics["target_calories"] * 0.35)
    result = ai.generate_recipe(body.dish, metrics, body.servings,
                                profile["diet"], budget)
    db.save_recipe(user["id"], body.dish, body.servings, result)
    return {"recipe": result, "metrics": metrics}


@app.get("/api/recipes")
def recipe_history(user: dict = Depends(current_user)):
    return {"recipes": db.list_recipes(user["id"])}


# ===========================================================================
# Goal tracker
# ===========================================================================
@app.post("/api/log")
def add_log(body: LogIn, user: dict = Depends(current_user)):
    import datetime
    log_date = body.log_date or datetime.date.today().isoformat()
    summ = ai.summarize_log(body.note_text)
    lid = db.add_log(user["id"], log_date, body.note_text, summ["summary"],
                     summ["activity_score"], body.weight_kg)
    return {"id": lid, "ai": summ, "stats": db.log_stats(user["id"])}


@app.get("/api/logs")
def get_logs(user: dict = Depends(current_user)):
    return {"logs": db.list_logs(user["id"]), "stats": db.log_stats(user["id"])}


# ===========================================================================
# Reviews
# ===========================================================================
@app.post("/api/review")
def add_review(body: ReviewIn, user: dict = Depends(current_user)):
    rid = db.add_review(user["id"], body.feature, body.rating, body.comment)
    return {"id": rid, "ok": True}


@app.get("/api/reviews")
def get_reviews(user: dict = Depends(current_user)):
    return {"reviews": db.list_reviews(user["id"])}


# ===========================================================================
# Frontend
# ===========================================================================
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
