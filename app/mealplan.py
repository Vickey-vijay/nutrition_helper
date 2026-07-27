"""Region-aware meal-plan builder.

A meal is assembled as a *plate*, not a single dish. Indian meals are
structural: a carb base (staple), a protein centrepiece (main), a dry
vegetable (side) and a liquid/relish (accompaniment). Sambar and rasam sit
beside rice; they are not dinner. `app/foods.py` tags every dish with the role
it plays, and the templates below combine those roles into plates a household
would actually recognise.

Portioning works outward from the plate rather than inflating one dish: each
item gets a share of the meal's calorie budget, is clamped to a believable
multiple of its own serving size, and countable items (rotis, idlis, dosas)
are rounded to whole pieces. Nutrition is always computed from the
IFCT-referenced per-100g values in the database, never from the LLM.
"""
from __future__ import annotations
import random

from .database import query_foods
from .foods import keywords_for

# Share of the day's calories allotted to each meal.
SLOT_SHARE = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.30,
    "snack": 0.10,
}

# Which roles make up each meal, and how the meal's calories divide between
# them. A South lunch leans on rice, a North dinner on roti, but the structure
# is the same everywhere: base + centrepiece + vegetable + relish.
SLOT_TEMPLATES = {
    "breakfast": [("staple", 0.62), ("accompaniment", 0.38)],
    "lunch": [("staple", 0.40), ("main", 0.30), ("side", 0.18),
              ("accompaniment", 0.12)],
    "dinner": [("staple", 0.42), ("main", 0.34), ("side", 0.24)],
    "snack": [("snack", 1.0)],
}

# How far a single portion may stray from that dish's realistic serving size.
# The upper bound is what stops "750 g of rasam" from ever being generated.
MIN_SERVING_FACTOR = 0.75
MAX_SERVING_FACTOR = 2.0

# Dishes served as discrete pieces — portions round to whole units so the plan
# reads "Roti x 3" rather than "Roti 118 g".
_COUNTABLE = (
    "roti", "chapati", "phulka", "naan", "kulcha", "paratha", "poori", "puri",
    "bhatura", "luchi", "idli", "dosa", "uttapam", "appam", "vada", "papad",
    "appalam", "thepla", "chilla", "paniyaram", "modak", "kozhukattai",
)


def _matches(name: str, keywords: list[str]) -> bool:
    low = name.lower()
    return any(k in low for k in keywords)


def _is_countable(food: dict) -> bool:
    return _matches(food["name"], list(_COUNTABLE))


def _macros_for_grams(food: dict, grams: float) -> dict:
    factor = grams / 100.0
    return {
        "kcal": round(food["kcal"] * factor, 1),
        "protein_g": round(food["protein_g"] * factor, 1),
        "carb_g": round(food["carb_g"] * factor, 1),
        "fat_g": round(food["fat_g"] * factor, 1),
        "fibre_g": round(food["fibre_g"] * factor, 1),
    }


def _portion_grams(food: dict, kcal_budget: float) -> tuple[int, int | None]:
    """Grams for this dish given its slice of the meal budget.

    Returns (grams, pieces) where pieces is None for dishes served by weight.
    """
    serving = max(float(food["serving_g"]), 1.0)
    lo, hi = serving * MIN_SERVING_FACTOR, serving * MAX_SERVING_FACTOR

    if food["kcal"] <= 0:
        grams = serving
    else:
        grams = (kcal_budget / food["kcal"]) * 100.0
    grams = max(lo, min(grams, hi))

    if _is_countable(food):
        pieces = max(1, round(grams / serving))
        return int(round(pieces * serving)), pieces
    return int(round(grams)), None


def _pick(candidates: list[dict], rng: random.Random,
          liked_kw: list[str], used: set[str]) -> dict | None:
    """Choose a dish, preferring liked categories and avoiding repeats."""
    pool = [c for c in candidates if c["name"] not in used]
    if not pool:
        pool = candidates
    if not pool:
        return None
    if liked_kw:
        preferred = [c for c in pool if _matches(c["name"], liked_kw)]
        if preferred:
            pool = preferred
    return rng.choice(pool)


def _build_meal(foods: list[dict], slot: str, kcal_budget: float,
                rng: random.Random, liked_kw: list[str],
                used: set[str]) -> list[dict]:
    """Assemble one plate for `slot` from role-tagged dishes."""
    template = SLOT_TEMPLATES.get(slot, [("staple", 1.0)])
    by_role: dict[str, list[dict]] = {}
    for f in foods:
        if f["meal_slot"] == slot:
            by_role.setdefault(f["role"], []).append(f)

    items: list[dict] = []
    for role, share in template:
        candidates = by_role.get(role)
        if not candidates:
            # Region/diet combination has no dish in this role for this slot;
            # skip it rather than substituting something structurally wrong.
            continue
        food = _pick(candidates, rng, liked_kw, used)
        if not food:
            continue
        used.add(food["name"])
        grams, pieces = _portion_grams(food, kcal_budget * share)
        items.append({
            "slot": slot,
            "name": food["name"],
            "region": food["region"],
            "diet": food["diet"],
            "role": food["role"],
            "grams": grams,
            "pieces": pieces,
            **_macros_for_grams(food, grams),
        })
    return items


def _rebalance(items: list[dict], foods: list[dict],
               target_calories: int) -> None:
    """Nudge portions toward the day's target, in place.

    Scaling is applied per item and re-clamped to that dish's realistic range,
    so closing a calorie gap can never reintroduce an absurd portion. Two
    passes are enough to converge for any reachable target.
    """
    base_by_name = {f["name"]: f for f in foods}
    for _ in range(2):
        total = sum(i["kcal"] for i in items)
        if total <= 0:
            return
        scale = target_calories / total
        if 0.98 <= scale <= 1.02:
            return
        for it in items:
            base = base_by_name.get(it["name"])
            if not base:
                continue
            serving = max(float(base["serving_g"]), 1.0)
            lo, hi = serving * MIN_SERVING_FACTOR, serving * MAX_SERVING_FACTOR
            grams = max(lo, min(it["grams"] * scale, hi))
            if it.get("pieces") is not None:
                pieces = max(1, round(grams / serving))
                it["pieces"] = pieces
                grams = pieces * serving
            it["grams"] = int(round(grams))
            it.update(_macros_for_grams(base, it["grams"]))


def _available_foods(region: str, diet: str, prefs: dict | None) -> list[dict]:
    foods = query_foods(region=region, diet=diet)
    prefs = prefs or {}
    disliked_kw = keywords_for(prefs.get("disliked", []))
    if disliked_kw:
        filtered = [f for f in foods if not _matches(f["name"], disliked_kw)]
        # Only honour the filter while it still leaves enough to build plates.
        if len(filtered) >= 12:
            foods = filtered
    return foods


def build_day_plan(region: str, diet: str, target_calories: int,
                   seed: int | None = None, prefs: dict | None = None,
                   exclude_names: list[str] | None = None) -> dict:
    """Build one day of meals for a region, diet and calorie target.

    `prefs` is {"liked": [...], "disliked": [...]} of food-card keys: liked
    categories are favoured, disliked ones filtered out. `exclude_names`
    suppresses dishes already used elsewhere (see `build_week_plan`).
    `seed=None` produces a different plan on every call.
    """
    rng = random.Random(seed)
    foods = _available_foods(region, diet, prefs)
    liked_kw = keywords_for((prefs or {}).get("liked", []))

    used: set[str] = set(exclude_names or [])
    items: list[dict] = []
    for slot, share in SLOT_SHARE.items():
        items.extend(_build_meal(foods, slot, target_calories * share,
                                 rng, liked_kw, used))

    _rebalance(items, foods, target_calories)

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


def build_week_plan(region: str, diet: str, target_calories: int,
                    days: int = 7, prefs: dict | None = None,
                    seed: int | None = None) -> dict:
    """Build `days` consecutive days, carrying recent dishes forward as
    exclusions so the week does not repeat the same few plates.

    Exclusions decay: only the previous two days are suppressed, which keeps
    variety high without exhausting the smaller regional/diet pools.
    """
    rng = random.Random(seed)
    history: list[list[str]] = []
    plans = []
    for day in range(days):
        recent = [n for prev in history[-2:] for n in prev]
        plan = build_day_plan(region, diet, target_calories,
                              seed=rng.randrange(2**31), prefs=prefs,
                              exclude_names=recent)
        plans.append(plan)
        history.append([m["name"] for m in plan["meals"]])

    dishes = [m["name"] for p in plans for m in p["meals"]]
    return {
        "region": region,
        "diet": diet,
        "target_calories": target_calories,
        "days": plans,
        "distinct_dishes": len(set(dishes)),
        "total_dishes": len(dishes),
    }
