"""Region-aware day meal-plan builder.

Greedily assembles breakfast, lunch, dinner and a snack from region- and
diet-appropriate foods, scaling serving sizes so the day's total lands close
to the user's caloric target. Nutrition is computed from IFCT-referenced
per-100g values (never from the LLM).
"""
from __future__ import annotations
import random
from .database import query_foods
from .foods import keywords_for


def _matches(name: str, keywords: list[str]) -> bool:
    low = name.lower()
    return any(k in low for k in keywords)

# Share of daily calories per meal slot
SLOT_SHARE = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.30,
    "snack": 0.10,
}


def _macros_for_grams(food: dict, grams: float) -> dict:
    factor = grams / 100.0
    return {
        "kcal": round(food["kcal"] * factor, 1),
        "protein_g": round(food["protein_g"] * factor, 1),
        "carb_g": round(food["carb_g"] * factor, 1),
        "fat_g": round(food["fat_g"] * factor, 1),
        "fibre_g": round(food["fibre_g"] * factor, 1),
    }


def _pick_for_slot(foods: list[dict], slot: str, kcal_budget: float,
                   rng: random.Random, liked_kw: list[str] | None = None) -> dict | None:
    candidates = [f for f in foods if f["meal_slot"] == slot]
    if not candidates:
        # fall back to any food if a slot is empty for this region/diet
        candidates = foods
    if not candidates:
        return None

    # Bias toward liked foods when any liked candidate exists for this slot.
    if liked_kw:
        preferred = [c for c in candidates if _matches(c["name"], liked_kw)]
        if preferred:
            candidates = preferred

    food = rng.choice(candidates)
    # scale serving to hit the slot budget, clamped to a sane range
    if food["kcal"] <= 0:
        grams = food["serving_g"]
    else:
        grams = (kcal_budget / food["kcal"]) * 100.0
        grams = max(0.5 * food["serving_g"], min(grams, 3.0 * food["serving_g"]))
    grams = round(grams)
    macros = _macros_for_grams(food, grams)
    return {
        "slot": slot,
        "name": food["name"],
        "region": food["region"],
        "diet": food["diet"],
        "grams": grams,
        **macros,
    }


def build_day_plan(region: str, diet: str, target_calories: int,
                   seed: int | None = None, prefs: dict | None = None) -> dict:
    """Return a full day's plan plus aggregate nutrition totals.

    `prefs` is an optional {"liked": [...], "disliked": [...]} of food-card keys.
    Disliked categories are filtered out; liked categories are preferred.
    """
    rng = random.Random(seed)
    foods = query_foods(region=region, diet=diet)

    prefs = prefs or {}
    disliked_kw = keywords_for(prefs.get("disliked", []))
    liked_kw = keywords_for(prefs.get("liked", []))
    if disliked_kw:
        filtered = [f for f in foods if not _matches(f["name"], disliked_kw)]
        # keep the filter only if it leaves enough variety to build a plan
        if len(filtered) >= 4:
            foods = filtered

    items: list[dict] = []
    for slot, share in SLOT_SHARE.items():
        budget = target_calories * share
        pick = _pick_for_slot(foods, slot, budget, rng, liked_kw)
        if pick:
            items.append(pick)

    # Normalisation pass: nudge servings so the day total lands close to target,
    # keeping each portion within a realistic 0.4x-4x serving range.
    raw_total = sum(i["kcal"] for i in items)
    if raw_total > 0:
        scale = target_calories / raw_total
        for it in items:
            base = next(f for f in foods if f["name"] == it["name"])
            new_g = it["grams"] * scale
            new_g = max(0.4 * base["serving_g"], min(new_g, 4.0 * base["serving_g"]))
            it["grams"] = round(new_g)
            it.update(_macros_for_grams(base, it["grams"]))

    totals = {
        "kcal": round(sum(i["kcal"] for i in items), 1),
        "protein_g": round(sum(i["protein_g"] for i in items), 1),
        "carb_g": round(sum(i["carb_g"] for i in items), 1),
        "fat_g": round(sum(i["fat_g"] for i in items), 1),
        "fibre_g": round(sum(i["fibre_g"] for i in items), 1),
    }
    return {
        "region": region,
        "diet": diet,
        "target_calories": target_calories,
        "meals": items,
        "totals": totals,
        "calorie_accuracy_pct": round(
            100.0 * totals["kcal"] / target_calories, 1) if target_calories else 0,
    }
