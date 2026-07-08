"""Seed dataset of region-tagged Indian foods.

Per-100g macro values are referenced against the Indian Food Composition
Tables (IFCT 2017, NIN/ICMR) and standard published values for prepared
dishes. Values are representative of typical home preparation.

Fields per food:
  name, region (North/South/East/West/Pan-India), diet (veg/nonveg/vegan),
  meal_slot (breakfast/lunch/dinner/snack), serving_g (typical serving),
  kcal, protein_g, carb_g, fat_g, fibre_g   (all per 100 g)
"""

FOODS = [
    # ---------------- SOUTH ----------------
    ("Idli", "South", "vegan", "breakfast", 120, 139, 4.6, 28.0, 0.5, 1.2),
    ("Plain Dosa", "South", "vegan", "breakfast", 90, 168, 4.0, 29.0, 3.7, 1.5),
    ("Masala Dosa", "South", "veg", "breakfast", 150, 196, 4.2, 30.0, 6.5, 2.4),
    ("Medu Vada", "South", "vegan", "snack", 60, 245, 7.0, 26.0, 12.0, 3.5),
    ("Sambar", "South", "vegan", "lunch", 200, 85, 4.2, 11.5, 2.5, 3.0),
    ("Coconut Chutney", "South", "vegan", "snack", 40, 195, 3.0, 6.0, 18.0, 4.0),
    ("Curd Rice", "South", "veg", "lunch", 250, 132, 3.5, 22.0, 3.2, 0.8),
    ("Lemon Rice", "South", "vegan", "lunch", 200, 175, 3.2, 30.0, 4.8, 1.4),
    ("Pongal (Ven)", "South", "veg", "breakfast", 200, 165, 5.0, 26.0, 4.5, 1.8),
    ("Akki Roti", "South", "vegan", "breakfast", 100, 210, 4.0, 42.0, 3.0, 2.5),
    ("Kozhukattai", "South", "vegan", "snack", 80, 215, 3.6, 40.0, 5.0, 2.0),
    ("Fish Curry (Kerala)", "South", "nonveg", "lunch", 180, 135, 14.0, 4.0, 7.0, 0.6),
    ("Rasam", "South", "vegan", "dinner", 200, 45, 1.8, 7.0, 1.2, 1.0),
    ("Upma", "South", "vegan", "breakfast", 180, 155, 3.8, 25.0, 4.5, 1.6),

    # ---------------- NORTH ----------------
    ("Roti (Whole Wheat)", "North", "vegan", "lunch", 40, 297, 11.0, 51.0, 7.5, 9.0),
    ("Tandoori Roti", "North", "vegan", "dinner", 50, 285, 10.0, 53.0, 4.0, 8.0),
    ("Dal Makhani", "North", "veg", "dinner", 180, 145, 6.5, 13.0, 7.5, 5.0),
    ("Rajma", "North", "vegan", "lunch", 180, 140, 7.0, 19.0, 3.5, 6.5),
    ("Chole (Chickpea)", "North", "vegan", "lunch", 180, 165, 8.0, 22.0, 5.0, 7.0),
    ("Paneer Butter Masala", "North", "veg", "dinner", 150, 240, 9.0, 8.0, 19.0, 1.5),
    ("Aloo Paratha", "North", "veg", "breakfast", 120, 245, 5.5, 36.0, 8.5, 3.2),
    ("Palak Paneer", "North", "veg", "dinner", 180, 155, 8.0, 6.0, 11.0, 2.8),
    ("Butter Chicken", "North", "nonveg", "dinner", 200, 195, 15.0, 6.0, 12.0, 0.8),
    ("Jeera Rice", "North", "vegan", "lunch", 200, 165, 3.2, 32.0, 3.0, 1.0),
    ("Lassi (Sweet)", "North", "veg", "snack", 250, 95, 3.0, 14.0, 3.0, 0.0),
    ("Chana Masala", "North", "vegan", "lunch", 180, 155, 7.5, 23.0, 4.0, 6.0),
    ("Paneer Tikka", "North", "veg", "snack", 120, 230, 14.0, 6.0, 17.0, 1.2),

    # ---------------- EAST ----------------
    ("Steamed Rice", "East", "vegan", "lunch", 200, 130, 2.7, 28.0, 0.3, 0.4),
    ("Macher Jhol (Fish Curry)", "East", "nonveg", "lunch", 200, 120, 13.0, 4.0, 6.0, 0.7),
    ("Litti Chokha", "East", "vegan", "lunch", 150, 230, 6.5, 36.0, 7.0, 5.0),
    ("Cholar Dal", "East", "veg", "lunch", 180, 150, 6.0, 20.0, 4.5, 5.5),
    ("Aloo Posto", "East", "vegan", "dinner", 150, 175, 4.0, 18.0, 9.0, 3.0),
    ("Shukto", "East", "vegan", "dinner", 180, 95, 3.0, 12.0, 4.0, 4.0),
    ("Chingri Malai Curry", "East", "nonveg", "dinner", 180, 185, 14.0, 6.0, 11.0, 0.6),
    ("Pakhala (Fermented Rice)", "East", "vegan", "breakfast", 250, 88, 2.0, 19.0, 0.3, 0.5),
    ("Sandesh", "East", "veg", "snack", 60, 245, 9.0, 30.0, 9.0, 0.0),
    ("Luchi", "East", "vegan", "breakfast", 50, 320, 6.0, 45.0, 13.0, 2.5),

    # ---------------- WEST ----------------
    ("Dhokla", "West", "vegan", "snack", 100, 160, 6.0, 24.0, 4.0, 3.0),
    ("Thepla", "West", "vegan", "breakfast", 60, 265, 7.0, 40.0, 8.5, 4.5),
    ("Pav Bhaji", "West", "veg", "dinner", 250, 175, 4.5, 22.0, 8.0, 4.0),
    ("Poha", "West", "vegan", "breakfast", 180, 130, 2.6, 25.0, 2.5, 1.2),
    ("Misal Pav", "West", "vegan", "breakfast", 220, 185, 7.5, 24.0, 6.5, 6.0),
    ("Undhiyu", "West", "vegan", "lunch", 200, 145, 4.5, 16.0, 7.5, 5.5),
    ("Bombil Fry (Bombay Duck)", "West", "nonveg", "lunch", 120, 165, 16.0, 6.0, 8.0, 0.4),
    ("Gujarati Kadhi", "West", "veg", "lunch", 200, 85, 3.2, 9.0, 4.0, 0.6),
    ("Sol Kadhi", "West", "vegan", "dinner", 200, 65, 1.2, 7.0, 4.0, 0.8),
    ("Khaman", "West", "vegan", "snack", 100, 170, 7.0, 25.0, 4.5, 3.2),
    ("Batata Vada", "West", "vegan", "snack", 70, 240, 4.5, 30.0, 11.0, 2.8),

    # ---------------- PAN-INDIA staples (fit any region) ----------------
    ("Mixed Vegetable Sabzi", "Pan-India", "vegan", "dinner", 180, 95, 3.0, 11.0, 4.5, 4.0),
    ("Moong Dal", "Pan-India", "vegan", "lunch", 180, 130, 8.0, 18.0, 2.0, 5.0),
    ("Boiled Egg", "Pan-India", "nonveg", "breakfast", 100, 155, 13.0, 1.1, 11.0, 0.0),
    ("Banana", "Pan-India", "vegan", "snack", 120, 89, 1.1, 23.0, 0.3, 2.6),
    ("Curd (Plain Yogurt)", "Pan-India", "veg", "snack", 150, 60, 3.1, 4.7, 3.3, 0.0),
    ("Roasted Chana", "Pan-India", "vegan", "snack", 50, 364, 18.0, 51.0, 6.0, 18.0),
]

# Column order for DB insertion
COLUMNS = ["name", "region", "diet", "meal_slot", "serving_g",
           "kcal", "protein_g", "carb_g", "fat_g", "fibre_g"]


# ---------------------------------------------------------------------------
# Food-preference cards
# ---------------------------------------------------------------------------
# Tap-to-pick ingredient/category cards shown on the "Food Preferences" screen.
# Each card maps to keywords used to match dishes in FOODS, so a user's likes
# and dislikes can bias (or filter) the generated meal plan. Emoji are used as
# zero-dependency, offline-friendly visuals (no image hosting required).
FOOD_CARDS = [
    {"key": "paneer",  "label": "Paneer",         "emoji": "🧀",
     "keywords": ["paneer"]},
    {"key": "chicken", "label": "Chicken",        "emoji": "🍗",
     "keywords": ["chicken"]},
    {"key": "fish",    "label": "Fish & Seafood", "emoji": "🐟",
     "keywords": ["fish", "macher", "chingri", "bombil"]},
    {"key": "egg",     "label": "Egg",            "emoji": "🥚",
     "keywords": ["egg"]},
    {"key": "rice",    "label": "Rice & Dosa",    "emoji": "🍚",
     "keywords": ["rice", "dosa", "idli", "pongal", "pakhala", "upma"]},
    {"key": "wheat",   "label": "Roti & Wheat",   "emoji": "🫓",
     "keywords": ["roti", "paratha", "thepla", "luchi", "litti"]},
    {"key": "dal",     "label": "Dal & Legumes",  "emoji": "🫘",
     "keywords": ["dal", "rajma", "chole", "chana", "moong", "sambar", "cholar"]},
    {"key": "greens",  "label": "Leafy Greens",   "emoji": "🥬",
     "keywords": ["palak", "saag", "shukto", "sabzi", "undhiyu"]},
    {"key": "fruit",   "label": "Fruits",         "emoji": "🍌",
     "keywords": ["banana", "fruit"]},
    {"key": "dairy",   "label": "Curd & Dairy",   "emoji": "🥛",
     "keywords": ["curd", "lassi", "yogurt", "kadhi", "sandesh"]},
    {"key": "nuts",    "label": "Nuts & Seeds",   "emoji": "🥜",
     "keywords": ["chana", "posto", "peanut"]},
    {"key": "fried",   "label": "Fried Snacks",   "emoji": "🍟",
     "keywords": ["vada", "bhaji", "batata", "fry", "khaman", "pakora", "luchi"]},
]

_CARD_BY_KEY = {c["key"]: c for c in FOOD_CARDS}


def keywords_for(keys: list[str]) -> list[str]:
    """Flatten the keyword lists for a set of food-card keys."""
    out: list[str] = []
    for k in keys or []:
        card = _CARD_BY_KEY.get(k)
        if card:
            out.extend(card["keywords"])
    return out
