"""AI guidance layer for NutriMind AI — LangChain + Groq.

Uses the Groq free-tier LLM (Llama 3.x) orchestrated through LangChain when
GROQ_API_KEY is configured; otherwise falls back to a deterministic,
rule-based generator so the system is always fully functional with zero
configuration and zero cost.

Core design rule (from the project KT note): the LLM writes recipe and
guidance TEXT only. All calorie/macro NUMBERS come from the IFCT-referenced
database and the Python nutrition engine — never invented by the model. Where
the model returns an estimate (e.g. a free-text recipe), it is clearly
labelled "approx" alongside the Python-derived calorie budget.
"""
from __future__ import annotations
import os
from typing import Optional

from pydantic import BaseModel, Field

# LangChain / Groq are optional at runtime: if the import or the API call
# fails for any reason, we degrade gracefully to the rule-based fallback.
try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    _LC_AVAILABLE = True
except Exception:  # pragma: no cover - only when deps missing
    _LC_AVAILABLE = False


def ai_enabled() -> bool:
    return _LC_AVAILABLE and bool(os.environ.get("GROQ_API_KEY"))


def ai_mode() -> str:
    return "groq_llama_langchain" if ai_enabled() else "rule_based_fallback"


def _model(temperature: float = 0.4, max_tokens: int = 700):
    return ChatGroq(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=30,
        max_retries=1,
    )


# ===========================================================================
# 1. Meal-plan guidance
# ===========================================================================
def _guidance_prompt(plan: dict, metrics: dict, prefs: dict) -> str:
    meals = "\n".join(
        f"- {m['slot'].title()}: {m['name']} ({m['grams']} g, {m['kcal']} kcal)"
        for m in plan["meals"]
    )
    likes = ", ".join(prefs.get("liked", [])) or "none specified"
    dislikes = ", ".join(prefs.get("disliked", [])) or "none specified"
    return (
        "You are a registered Indian dietitian. Give concise, practical "
        f"guidance for this regional ({plan['region']}) {plan['diet']} day "
        f"meal plan. The user's BMI is {metrics['bmi']} "
        f"({metrics['bmi_category']}) with a daily target of "
        f"{plan['target_calories']} kcal.\n"
        f"Liked foods: {likes}. Disliked: {dislikes}.\n\n"
        f"Meal plan:\n{meals}\n\n"
        "For each meal give one line: a short cooking tip and a health note. "
        "End with 2 overall tips tailored to their BMI category. Keep it under "
        "180 words. Do NOT invent or restate calorie numbers."
    )


def meal_guidance(plan: dict, metrics: dict, prefs: dict | None = None) -> dict:
    prefs = prefs or {"liked": [], "disliked": []}
    if ai_enabled():
        try:
            msg = _model(0.4, 450).invoke(_guidance_prompt(plan, metrics, prefs))
            text = (msg.content or "").strip()
            if text:
                return {"source": "groq_llama_langchain", "guidance": text}
        except Exception:
            pass
    return {"source": "rule_based_fallback",
            "guidance": _rule_based_guidance(plan, metrics["bmi_category"])}


# ===========================================================================
# 2. AI goal recommendation (replaces the manual goal dropdown)
# ===========================================================================
class GoalOut(BaseModel):
    goal: str = Field(description="one of: lose, maintain, gain")
    rationale: str = Field(description="one short sentence, friendly tone")


def suggest_goal(metrics: dict) -> dict:
    """Let the AI recommend lose/maintain/gain from the biometric picture."""
    cat = metrics["bmi_category"]
    if ai_enabled():
        try:
            llm = _model(0.2, 200).with_structured_output(GoalOut)
            prompt = (
                "A user has BMI "
                f"{metrics['bmi']} (category {cat}), BMR "
                f"{metrics['bmr']} kcal and TDEE {metrics['tdee']} kcal. "
                "Recommend a single weight goal (lose, maintain, or gain) and "
                "a one-sentence rationale. Be safe and evidence-based."
            )
            out: GoalOut = llm.invoke(prompt)
            goal = out.goal.lower().strip()
            if goal in ("lose", "maintain", "gain"):
                return {"source": "groq_llama_langchain", "goal": goal,
                        "rationale": out.rationale.strip()}
        except Exception:
            pass
    # Deterministic clinical fallback
    rule = {
        "Underweight": ("gain", "Your BMI is below the healthy range, so a lean "
                                "calorie surplus is recommended."),
        "Normal":     ("maintain", "Your BMI is in the healthy range — maintain "
                                   "with balanced intake."),
        "Overweight": ("lose", "A modest calorie deficit will move you toward a "
                               "healthier BMI."),
        "Obese":      ("lose", "A sustained, supervised deficit is advised to "
                               "reduce health risk."),
    }
    goal, why = rule.get(cat, ("maintain", "Maintain a balanced intake."))
    return {"source": "rule_based_fallback", "goal": goal, "rationale": why}


# ===========================================================================
# 3. Healthy recipe generator (scaled to the user)
# ===========================================================================
class RecipeOut(BaseModel):
    title: str
    servings: int
    ingredients: list[str] = Field(description="quantified ingredient lines")
    steps: list[str] = Field(description="numbered-style method steps")
    health_notes: list[str] = Field(description="2-3 short health/swap notes")
    approx_calories_per_serving: int = Field(
        description="model's best estimate of kcal per serving")
    prep_time_min: int


def generate_recipe(dish: str, metrics: dict, servings: int,
                    diet: str, budget_kcal: int) -> dict:
    """Healthiest version of `dish`, scaled to `servings`, designed to fit the
    Python-derived per-serving calorie `budget_kcal`."""
    if ai_enabled():
        try:
            llm = _model(0.5, 800).with_structured_output(RecipeOut)
            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are a healthy Indian home-cooking chef and dietitian. "
                 "Produce the healthiest practical version of the requested "
                 "dish: minimal oil, whole ingredients, balanced macros. "
                 "Respect the dietary preference strictly."),
                ("human",
                 "Dish: {dish}\nServings: {servings}\nDietary preference: {diet}\n"
                 "Target calorie budget per serving: about {budget} kcal "
                 "(suited to this user's body).\n"
                 "Give quantified ingredients for exactly {servings} serving(s), "
                 "clear method steps, 2-3 health notes, an approximate kcal per "
                 "serving, and prep time in minutes."),
            ])
            out: RecipeOut = (prompt | llm).invoke({
                "dish": dish, "servings": servings, "diet": diet,
                "budget": budget_kcal})
            data = out.model_dump()
            data["source"] = "groq_llama_langchain"
            data["budget_kcal_per_serving"] = budget_kcal
            return data
        except Exception:
            pass
    return _rule_based_recipe(dish, servings, diet, budget_kcal)


# ===========================================================================
# 4. Tracker note summariser (note -> summary + 1-10 activity score)
# ===========================================================================
class LogOut(BaseModel):
    summary: str = Field(description="one-line summary of the day's activity")
    activity_score: int = Field(description="effort/consistency score 1-10")
    encouragement: str = Field(description="one short motivating sentence")


def summarize_log(note_text: str) -> dict:
    if ai_enabled():
        try:
            llm = _model(0.3, 200).with_structured_output(LogOut)
            out: LogOut = llm.invoke(
                "Summarise this fitness/diet diary note in one line, rate the "
                "day's effort and consistency from 1 (none) to 10 (excellent), "
                "and add one motivating sentence.\n\nNote: " + note_text)
            score = max(1, min(10, int(out.activity_score)))
            return {"source": "groq_llama_langchain", "summary": out.summary.strip(),
                    "activity_score": score, "encouragement": out.encouragement.strip()}
        except Exception:
            pass
    return _rule_based_log(note_text)


# ===========================================================================
# Rule-based fallbacks
# ===========================================================================
_TIPS = {
    "Idli": "Steam 10-12 min until a toothpick comes out clean; pair with sambar for complete protein.",
    "Plain Dosa": "Spread batter thin on a hot tawa; use minimal oil to keep it light.",
    "Sambar": "Pressure-cook toor dal soft and temper with curry leaves and mustard seeds.",
    "Roti (Whole Wheat)": "Knead with warm water and rest 20 min for soft rotis; whole wheat adds fibre.",
    "Rajma": "Soak kidney beans overnight; high in plant protein and fibre.",
    "Dal Makhani": "Slow-simmer for the creamy texture; go easy on butter to cut saturated fat.",
    "Poha": "Rinse flattened rice briefly so it stays fluffy; add peanuts for protein.",
    "Dhokla": "Steam the fermented batter; a naturally low-fat, high-protein snack.",
    "Litti Chokha": "Roast litti over flame; the sattu filling is rich in plant protein.",
    "Macher Jhol (Fish Curry)": "Use a light mustard-tomato gravy; fish gives lean protein and omega-3.",
}


def _rule_based_guidance(plan: dict, bmi_category: str) -> str:
    lines = [
        f"Regional {plan['diet']} plan for {plan['region']} India "
        f"(BMI: {bmi_category}, target {plan['target_calories']} kcal):",
        "",
    ]
    for m in plan["meals"]:
        tip = _TIPS.get(m["name"],
                        "Use minimal oil and fresh local ingredients; "
                        "portion to the serving shown.")
        lines.append(f"• {m['slot'].title()} — {m['name']} ({m['grams']} g, "
                     f"{m['kcal']} kcal): {tip}")
    lines.append("")
    if bmi_category in ("Overweight", "Obese"):
        lines.append("Overall: favour the listed fibre-rich dals and vegetables, "
                     "limit fried snacks and added ghee, and keep portion sizes "
                     "to the gram amounts shown to stay within your deficit.")
    elif bmi_category == "Underweight":
        lines.append("Overall: add a glass of milk or a handful of nuts between "
                     "meals to reach your surplus, and include the protein-rich "
                     "items (paneer, dal, egg, fish) at each meal.")
    else:
        lines.append("Overall: keep the balance of dal, vegetable and grain shown; "
                     "stay hydrated and keep activity consistent to maintain weight.")
    lines.append("Tip: drink water before meals and prefer steamed/roasted "
                 "preparations over deep-fried for the same regional foods.")
    return "\n".join(lines)


def _rule_based_recipe(dish: str, servings: int, diet: str,
                       budget_kcal: int) -> dict:
    return {
        "source": "rule_based_fallback",
        "title": f"Healthy {dish.title()}",
        "servings": servings,
        "budget_kcal_per_serving": budget_kcal,
        "approx_calories_per_serving": budget_kcal,
        "prep_time_min": 30,
        "ingredients": [
            f"Base ingredients for {dish} (scaled to {servings} serving(s))",
            "1-2 tsp oil (minimal)",
            "Onion, tomato, ginger-garlic to taste",
            "Whole spices: cumin, turmeric, chilli, coriander",
            "Fresh coriander to garnish",
        ],
        "steps": [
            "Prep and chop all ingredients.",
            "Heat minimal oil; temper whole spices.",
            "Add aromatics and cook until soft.",
            f"Add the main components of {dish} and cook through.",
            "Simmer to desired consistency; adjust seasoning.",
            "Garnish and serve one portion per person.",
        ],
        "health_notes": [
            "Use minimal oil and prefer steaming/roasting over frying.",
            f"Portion to about {budget_kcal} kcal per serving for your body.",
            "Add a side salad or curd for fibre and protein balance.",
        ],
    }


def _rule_based_log(note_text: str) -> dict:
    t = note_text.lower()
    score = 5
    pos = sum(k in t for k in ("workout", "run", "gym", "walk", "yoga",
                               "exercise", "active", "steps", "cardio"))
    neg = sum(k in t for k in ("skipped", "lazy", "junk", "tired", "missed",
                               "cheat", "rest", "no exercise"))
    score = max(1, min(10, 5 + 2 * pos - 2 * neg))
    summary = (note_text[:90] + "…") if len(note_text) > 90 else note_text
    enc = ("Great consistency — keep the momentum!" if score >= 7
           else "Good effort — small steps add up, keep going!" if score >= 4
           else "Tomorrow is a fresh start — aim for one healthy choice.")
    return {"source": "rule_based_fallback", "summary": summary,
            "activity_score": score, "encouragement": enc}
