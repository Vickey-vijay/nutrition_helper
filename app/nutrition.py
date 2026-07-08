"""Clinical nutrition computations for NutriMind AI.

Implements:
  - WHO-standard BMI and category classification
  - Mifflin-St Jeor Basal Metabolic Rate (1990)
  - Harris-Benedict activity multipliers -> Total Daily Energy Expenditure (TDEE)
  - Goal-adjusted daily caloric target
"""
from __future__ import annotations
from datetime import date, datetime

# Harris-Benedict activity multipliers applied to BMR
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very": 1.725,
    "extra": 1.9,
}

ACTIVITY_LABELS = {
    "sedentary": "Sedentary (desk job, no exercise)",
    "light": "Lightly active (1-3 days/week)",
    "moderate": "Moderately active (3-5 days/week)",
    "very": "Very active (6-7 days/week)",
    "extra": "Extra active (physical job + training)",
}

# Goal -> calorie delta applied to TDEE
GOAL_ADJUSTMENTS = {
    "lose": -500,      # ~0.45 kg/week deficit
    "maintain": 0,
    "gain": 400,       # lean surplus
}


def age_from_dob(dob: str) -> int:
    """Whole-year age from an ISO date string (YYYY-MM-DD)."""
    try:
        d = datetime.strptime(dob, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("dob must be in YYYY-MM-DD format")
    today = date.today()
    years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    return max(years, 0)


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    """WHO BMI = weight(kg) / height(m)^2."""
    height_m = height_cm / 100.0
    if height_m <= 0:
        raise ValueError("height must be positive")
    return round(weight_kg / (height_m * height_m), 1)


def classify_bmi(bmi: float) -> str:
    """WHO (2000) BMI category thresholds."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal"
    if bmi < 30.0:
        return "Overweight"
    return "Obese"


def compute_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor BMR (1990).

    Men:   (10*kg) + (6.25*cm) - (5*age) + 5
    Women: (10*kg) + (6.25*cm) - (5*age) - 161
    """
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if sex.lower().startswith("m"):
        return round(base + 5, 1)
    return round(base - 161, 1)


def compute_tdee(bmr: float, activity: str) -> float:
    """Total daily energy expenditure = BMR * activity multiplier."""
    mult = ACTIVITY_MULTIPLIERS.get(activity, 1.2)
    return round(bmr * mult, 1)


def compute_target_calories(tdee: float, goal: str) -> int:
    """Apply goal adjustment, floored to a safe minimum."""
    target = tdee + GOAL_ADJUSTMENTS.get(goal, 0)
    return int(max(target, 1200))


def full_profile_metrics(age: int, sex: str, height_cm: float,
                         weight_kg: float, activity: str, goal: str) -> dict:
    """One-shot computation of all biometric metrics for a profile."""
    bmi = compute_bmi(weight_kg, height_cm)
    bmr = compute_bmr(weight_kg, height_cm, age, sex)
    tdee = compute_tdee(bmr, activity)
    target = compute_target_calories(tdee, goal)
    return {
        "bmi": bmi,
        "bmi_category": classify_bmi(bmi),
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": target,
        "activity_label": ACTIVITY_LABELS.get(activity, activity),
    }
