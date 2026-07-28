"""AI guidance layer for NutriMind AI — local quantised LLM, Groq, or rules.

Final-semester design: a **three-tier fallback chain**, tried in order for every
request, so the app is free, private and offline-capable when it can be and
still fully functional when it cannot:

    1. LOCAL   — a 4-bit (Q4_K_M) quantised GGUF running on the CPU through
                 llama-cpp-python (``app/llm_local.py``). Zero cost, zero
                 network, data never leaves the machine.
    2. GROQ    — the mid-semester cloud path (LangChain + Groq Llama 3.x), used
                 when no local model is installed but an API key is configured.
    3. RULES   — the deterministic rule-based generator. Always works, needs
                 nothing installed and no key.

The chain is configured with ``NUTRIMIND_AI_BACKEND`` in ``.env``:

    auto   (default)  local -> groq -> rules
    local             local -> rules          (never touches the network)
    groq              groq  -> rules
    rules             rules only

A tier that is unavailable — llama-cpp-python not installed, the GGUF not
downloaded, no API key, a call that errors or times out — is skipped silently
and the next one runs. No configuration can make the app crash or return
nothing.

Core design rule (unchanged from the mid-semester build): the LLM writes recipe
and guidance TEXT only. All calorie/macro NUMBERS come from the IFCT-referenced
database and the Python nutrition engine — never invented by the model. Where
the model returns an estimate (e.g. a free-text recipe), it is clearly labelled
"approx" alongside the Python-derived calorie budget.
"""
from __future__ import annotations
import os
from typing import Optional

from pydantic import BaseModel, Field

from . import llm_local

# LangChain / Groq are optional at runtime: if the import or the API call
# fails for any reason, we degrade gracefully to the next tier.
try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    _LC_AVAILABLE = True
except Exception:  # pragma: no cover - only when deps missing
    _LC_AVAILABLE = False

# Source labels, also used as the tier names in /api/health.
SRC_LOCAL = "local_quantised_llama_cpp"
SRC_GROQ = "groq_llama_langchain"
SRC_RULES = "rule_based_fallback"

VALID_BACKENDS = ("auto", "local", "groq", "rules")

# Which tier actually served the most recent request. ``None`` until the first
# AI call — /api/health reports it as "not yet exercised".
_LAST_TIER: Optional[str] = None


# ===========================================================================
# Tier selection
# ===========================================================================
def backend_preference() -> str:
    """The configured ``NUTRIMIND_AI_BACKEND`` (unknown values fall back to auto)."""
    value = (os.environ.get("NUTRIMIND_AI_BACKEND") or "auto").strip().lower()
    return value if value in VALID_BACKENDS else "auto"


def local_available() -> bool:
    """True if the local quantised model could serve a request (cheap check)."""
    return llm_local.available()


def groq_available() -> bool:
    return _LC_AVAILABLE and bool(os.environ.get("GROQ_API_KEY"))


def _tier_order() -> list:
    """Tiers to try, in order, for the configured backend preference.

    ``auto`` puts Groq ahead of the local model on purpose. Measured on CPU,
    the quantised 7B answers a log summary in about 32 s and a recipe in about
    four and a half minutes (see docs/08_LOCAL_LLM_BENCHMARK.md), against
    roughly a second for the cloud tier. Trying local first would make an
    ordinary session feel broken, so ``auto`` means "the fastest tier that
    works" and the local model is what keeps the app running when there is no
    key and no network.

    ``local`` deliberately does NOT chain to Groq: someone who pins the backend
    to local is asking for offline/private operation, and silently calling a
    cloud API would break that guarantee. It falls straight through to rules.
    That setting is also how the offline, zero-cost claim is demonstrated.
    """
    pref = backend_preference()
    if pref == "local":
        return [SRC_LOCAL, SRC_RULES]
    if pref == "groq":
        return [SRC_GROQ, SRC_RULES]
    if pref == "rules":
        return [SRC_RULES]
    return [SRC_GROQ, SRC_LOCAL, SRC_RULES]


def active_tier() -> str:
    """The tier that would serve a request right now."""
    for tier in _tier_order():
        if tier == SRC_LOCAL and local_available():
            return SRC_LOCAL
        if tier == SRC_GROQ and groq_available():
            return SRC_GROQ
        if tier == SRC_RULES:
            return SRC_RULES
    return SRC_RULES


def ai_enabled() -> bool:
    """True if a real LLM tier (local or cloud) is available."""
    return active_tier() in (SRC_LOCAL, SRC_GROQ)


def ai_mode() -> str:
    """Human/machine-readable name of the tier currently in front."""
    return active_tier()


def ai_status() -> dict:
    """Full AI-layer diagnostics for ``/api/health``.

    ``tier`` is what the next request will use; ``last_tier`` is what the most
    recent request actually used (they differ if, say, the local model is
    installed but the load failed mid-session).
    """
    tier = active_tier()
    local = llm_local.status()
    if tier == SRC_LOCAL:
        model = local.get("model_file")
    elif tier == SRC_GROQ:
        model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    else:
        model = None
    return {
        "tier": tier,
        "backend_preference": backend_preference(),
        "chain": _tier_order(),
        "last_tier": _LAST_TIER,
        "model": model,
        "local": local,
        "groq": {
            "available": groq_available(),
            "langchain_installed": _LC_AVAILABLE,
            "api_key_set": bool(os.environ.get("GROQ_API_KEY")),
            "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        },
        "rules": {"available": True},
    }


def _record(tier: str) -> str:
    global _LAST_TIER
    _LAST_TIER = tier
    return tier


def _try(tier: str) -> bool:
    """Should we attempt ``tier`` for this request?"""
    if tier == SRC_LOCAL:
        return llm_local.available()
    if tier == SRC_GROQ:
        return groq_available()
    return True


def _model(temperature: float = 0.4, max_tokens: int = 700):
    return ChatGroq(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=30,
        max_retries=1,
    )


DIETITIAN_SYSTEM = (
    "You are a registered Indian dietitian and healthy home-cooking chef. "
    "Be concise, practical and evidence-based. Never invent calorie numbers."
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
    prompt = _guidance_prompt(plan, metrics, prefs)

    for tier in _tier_order():
        if not _try(tier):
            continue

        if tier == SRC_LOCAL:
            text = llm_local.chat(prompt, system=DIETITIAN_SYSTEM,
                                  temperature=0.4, max_tokens=450)
            if text:
                return {"source": _record(SRC_LOCAL), "guidance": text}

        elif tier == SRC_GROQ:
            try:
                msg = _model(0.4, 450).invoke(prompt)
                text = (msg.content or "").strip()
                if text:
                    return {"source": _record(SRC_GROQ), "guidance": text}
            except Exception:
                pass

        else:
            break

    return {"source": _record(SRC_RULES),
            "guidance": _rule_based_guidance(plan, metrics["bmi_category"])}


# ===========================================================================
# 2. AI goal recommendation (replaces the manual goal dropdown)
# ===========================================================================
class GoalOut(BaseModel):
    goal: str = Field(description="one of: lose, maintain, gain")
    rationale: str = Field(description="one short sentence, friendly tone")


def _goal_prompt(metrics: dict, cat: str) -> str:
    return (
        "A user has BMI "
        f"{metrics['bmi']} (category {cat}), BMR "
        f"{metrics['bmr']} kcal and TDEE {metrics['tdee']} kcal. "
        "Recommend a single weight goal (lose, maintain, or gain) and "
        "a one-sentence rationale. Be safe and evidence-based."
    )


def suggest_goal(metrics: dict) -> dict:
    """Let the AI recommend lose/maintain/gain from the biometric picture."""
    cat = metrics["bmi_category"]
    prompt = _goal_prompt(metrics, cat)

    for tier in _tier_order():
        if not _try(tier):
            continue

        if tier == SRC_LOCAL:
            out = llm_local.chat_json(prompt, GoalOut, system=DIETITIAN_SYSTEM,
                                      temperature=0.2, max_tokens=200)
            if out:
                goal = out.goal.lower().strip()
                if goal in ("lose", "maintain", "gain"):
                    return {"source": _record(SRC_LOCAL), "goal": goal,
                            "rationale": out.rationale.strip()}

        elif tier == SRC_GROQ:
            try:
                llm = _model(0.2, 200).with_structured_output(GoalOut)
                out: GoalOut = llm.invoke(prompt)
                goal = out.goal.lower().strip()
                if goal in ("lose", "maintain", "gain"):
                    return {"source": _record(SRC_GROQ), "goal": goal,
                            "rationale": out.rationale.strip()}
            except Exception:
                pass

        else:
            break

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
    return {"source": _record(SRC_RULES), "goal": goal, "rationale": why}


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


_RECIPE_SYSTEM = (
    "You are a healthy Indian home-cooking chef and dietitian. "
    "Produce the healthiest practical version of the requested "
    "dish: minimal oil, whole ingredients, balanced macros. "
    "Respect the dietary preference strictly."
)

_RECIPE_HUMAN = (
    "Dish: {dish}\nServings: {servings}\nDietary preference: {diet}\n"
    "Target calorie budget per serving: about {budget} kcal "
    "(suited to this user's body).\n"
    "Give quantified ingredients for exactly {servings} serving(s), "
    "clear method steps, 2-3 health notes, an approximate kcal per "
    "serving, and prep time in minutes."
)


def generate_recipe(dish: str, metrics: dict, servings: int,
                    diet: str, budget_kcal: int) -> dict:
    """Healthiest version of `dish`, scaled to `servings`, designed to fit the
    Python-derived per-serving calorie `budget_kcal`."""
    fields = {"dish": dish, "servings": servings, "diet": diet,
              "budget": budget_kcal}

    for tier in _tier_order():
        if not _try(tier):
            continue

        if tier == SRC_LOCAL:
            out = llm_local.chat_json(_RECIPE_HUMAN.format(**fields), RecipeOut,
                                      system=_RECIPE_SYSTEM, temperature=0.5,
                                      max_tokens=900)
            if out and out.ingredients and out.steps:
                data = out.model_dump()
                data["source"] = _record(SRC_LOCAL)
                data["budget_kcal_per_serving"] = budget_kcal
                return data

        elif tier == SRC_GROQ:
            try:
                llm = _model(0.5, 800).with_structured_output(RecipeOut)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", _RECIPE_SYSTEM),
                    ("human", _RECIPE_HUMAN),
                ])
                out: RecipeOut = (prompt | llm).invoke(fields)
                data = out.model_dump()
                data["source"] = _record(SRC_GROQ)
                data["budget_kcal_per_serving"] = budget_kcal
                return data
            except Exception:
                pass

        else:
            break

    _record(SRC_RULES)
    return _rule_based_recipe(dish, servings, diet, budget_kcal)


# ===========================================================================
# 4. Tracker note summariser (note -> summary + 1-10 activity score)
# ===========================================================================
class LogOut(BaseModel):
    summary: str = Field(description="one-line summary of the day's activity")
    activity_score: int = Field(description="effort/consistency score 1-10")
    encouragement: str = Field(description="one short motivating sentence")


def summarize_log(note_text: str) -> dict:
    prompt = (
        "Summarise this fitness/diet diary note in one line, rate the "
        "day's effort and consistency from 1 (none) to 10 (excellent), "
        "and add one motivating sentence.\n\nNote: " + note_text)

    for tier in _tier_order():
        if not _try(tier):
            continue

        if tier == SRC_LOCAL:
            out = llm_local.chat_json(prompt, LogOut, system=DIETITIAN_SYSTEM,
                                      temperature=0.3, max_tokens=250)
            if out and out.summary.strip():
                score = max(1, min(10, int(out.activity_score)))
                return {"source": _record(SRC_LOCAL),
                        "summary": out.summary.strip(),
                        "activity_score": score,
                        "encouragement": out.encouragement.strip()}

        elif tier == SRC_GROQ:
            try:
                llm = _model(0.3, 200).with_structured_output(LogOut)
                out: LogOut = llm.invoke(prompt)
                score = max(1, min(10, int(out.activity_score)))
                return {"source": _record(SRC_GROQ),
                        "summary": out.summary.strip(),
                        "activity_score": score,
                        "encouragement": out.encouragement.strip()}
            except Exception:
                pass

        else:
            break

    _record(SRC_RULES)
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
        "source": SRC_RULES,
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
            # Curd is dairy, so the balance suggestion has to respect a vegan
            # request the same way the LLM path is instructed to.
            "Add a side salad or a lentil side for fibre and protein balance."
            if diet == "vegan" else
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
    return {"source": SRC_RULES, "summary": summary,
            "activity_score": score, "encouragement": enc}
