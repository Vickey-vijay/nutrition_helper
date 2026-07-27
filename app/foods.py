"""Seed dataset of region-tagged Indian foods.

Per-100g macro values are referenced against the Indian Food Composition
Tables (IFCT 2017, NIN/ICMR) and standard published values for prepared
dishes. Values are representative of typical home preparation.

Fields per food:
  name       - dish name (unique; doubles as the display label)
  region     - North / South / East / West / Pan-India
  diet       - veg / nonveg / vegan
  meal_slot  - breakfast / lunch / dinner / snack
  role       - structural part the dish plays in a thali (see ROLES)
  serving_g  - ONE realistic human portion of that dish, in grams
  kcal, protein_g, carb_g, fat_g, fibre_g  - all per 100 g

Why `role` exists
-----------------
A meal is not "one random dish". An Indian plate is assembled from parts:
a carb base, a protein centrepiece, a dry vegetable and a liquid/relish
accompaniment. Sambar, rasam, kadhi, chutney, curd and raita are *never* a
standalone meal - they sit beside rice or roti. Tagging the structural role
lets the planner build a plate that a real household would recognise instead
of, say, serving 750 g of rasam for dinner.

Serving sizes are per-dish and deliberately asymmetric: a chutney is 30 g, a
roti is 40 g, a bowl of rasam is 150 g. The per-100g macros stay constant;
only the portion changes.
"""

# Structural role of a dish within a meal. Keep in sync with the planner.
ROLES = (
    "staple",         # carb base: rice, roti, chapati, dosa, idli, paratha
    "main",           # protein centrepiece: dal, rajma, chole, paneer, meat
    "side",           # dry vegetable dish: sabzi, poriyal, thoran, bhaji
    "accompaniment",  # sambar, rasam, kadhi, chutney, curd, pickle, raita
    "snack",          # vada, dhokla, roasted chana, fruit, lassi
    "sweet",          # sandesh, kheer, payasam
)

FOODS = [
    # =====================================================================
    # SOUTH  -  Tamil Nadu, Kerala, Karnataka, Andhra/Telangana
    # Rice-and-lentil led; fermented tiffin batters at breakfast, rice with
    # sambar/rasam and a dry poriyal at the main meals. Naturally vegan-rich
    # because coconut oil, not ghee, is the default cooking fat.
    # =====================================================================
    # -- breakfast staples (tiffin) --
    ("Idli", "South", "vegan", "breakfast", "staple", 100, 139, 4.6, 28.0, 0.5, 1.2),
    ("Plain Dosa", "South", "vegan", "breakfast", "staple", 90, 168, 4.0, 29.0, 3.7, 1.5),
    ("Masala Dosa", "South", "veg", "breakfast", "staple", 150, 196, 4.2, 30.0, 6.5, 2.4),
    ("Uttapam", "South", "vegan", "breakfast", "staple", 130, 170, 4.5, 28.0, 4.2, 2.0),
    ("Appam", "South", "vegan", "breakfast", "staple", 100, 148, 3.0, 30.0, 1.5, 1.0),
    ("Idiyappam (String Hoppers)", "South", "vegan", "breakfast", "staple", 120, 150, 3.0, 33.0, 0.6, 1.2),
    ("Rava Upma", "South", "vegan", "breakfast", "staple", 180, 155, 3.8, 25.0, 4.5, 1.6),
    ("Ven Pongal", "South", "veg", "breakfast", "staple", 200, 165, 5.0, 26.0, 4.5, 1.8),
    # -- breakfast accompaniments (what tiffin is actually eaten with) --
    ("Coconut Chutney", "South", "vegan", "breakfast", "accompaniment", 30, 195, 3.0, 6.0, 18.0, 4.0),
    ("Tiffin Sambar", "South", "vegan", "breakfast", "accompaniment", 120, 82, 4.0, 11.0, 2.4, 3.0),
    # -- lunch staples --
    ("Curd Rice", "South", "veg", "lunch", "staple", 200, 132, 3.5, 22.0, 3.2, 0.8),
    ("Lemon Rice", "South", "vegan", "lunch", "staple", 180, 175, 3.2, 30.0, 4.8, 1.4),
    ("Tamarind Rice (Puliyodarai)", "South", "vegan", "lunch", "staple", 180, 190, 3.5, 32.0, 5.5, 2.0),
    # -- lunch mains --
    ("Kootu (Lentil & Vegetable)", "South", "vegan", "lunch", "main", 150, 105, 5.0, 13.0, 3.5, 4.0),
    ("Paruppu (Tempered Toor Dal)", "South", "vegan", "lunch", "main", 150, 125, 7.5, 16.0, 3.2, 4.5),
    ("Kerala Fish Curry (Meen)", "South", "nonveg", "lunch", "main", 150, 135, 14.0, 4.0, 7.0, 0.6),
    ("Chettinad Chicken Curry", "South", "nonveg", "lunch", "main", 150, 190, 18.0, 5.0, 11.0, 1.2),
    ("Kerala Egg Roast", "South", "nonveg", "lunch", "main", 130, 165, 10.0, 6.0, 11.0, 1.0),
    # -- lunch sides --
    ("Beans Poriyal", "South", "vegan", "lunch", "side", 100, 95, 3.0, 9.0, 5.0, 4.0),
    ("Cabbage Thoran", "South", "vegan", "lunch", "side", 100, 105, 2.5, 8.5, 7.0, 3.5),
    ("Avial", "South", "veg", "lunch", "side", 120, 115, 2.8, 9.0, 7.5, 3.2),
    # -- lunch accompaniments --
    ("Sambar", "South", "vegan", "lunch", "accompaniment", 150, 85, 4.2, 11.5, 2.5, 3.0),
    ("Tomato Chutney", "South", "vegan", "lunch", "accompaniment", 30, 105, 2.0, 9.0, 6.5, 2.2),
    ("Appalam (Roasted Papad)", "South", "vegan", "lunch", "accompaniment", 15, 350, 21.0, 54.0, 3.5, 9.0),
    # -- dinner staples (lighter tiffin/millet at night) --
    ("Set Dosa", "South", "vegan", "dinner", "staple", 120, 175, 4.2, 30.0, 4.0, 1.8),
    ("Neer Dosa", "South", "vegan", "dinner", "staple", 100, 155, 2.8, 30.0, 2.5, 1.0),
    ("Ragi Mudde (Finger Millet)", "South", "vegan", "dinner", "staple", 150, 145, 3.4, 31.0, 0.8, 3.6),
    # -- dinner mains --
    ("Kadala Curry (Black Chickpea)", "South", "vegan", "dinner", "main", 150, 155, 7.5, 20.0, 5.0, 6.5),
    ("Kerala Vegetable Stew", "South", "vegan", "dinner", "main", 180, 110, 2.6, 11.0, 6.5, 2.8),
    ("Kerala Fish Moilee", "South", "nonveg", "dinner", "main", 150, 145, 13.5, 5.0, 8.0, 0.8),
    ("Andhra Chicken Pulusu", "South", "nonveg", "dinner", "main", 150, 160, 16.0, 6.0, 8.0, 1.4),
    # -- dinner sides --
    ("Beetroot Poriyal", "South", "vegan", "dinner", "side", 100, 90, 2.0, 11.0, 4.5, 3.0),
    ("Vazhakkai Fry (Raw Banana)", "South", "vegan", "dinner", "side", 100, 130, 1.8, 20.0, 5.0, 3.4),
    ("Keerai Masiyal (Mashed Greens)", "South", "vegan", "dinner", "side", 120, 75, 4.0, 6.0, 3.6, 3.5),
    # -- dinner accompaniments --
    ("Rasam", "South", "vegan", "dinner", "accompaniment", 150, 45, 1.8, 7.0, 1.2, 1.0),
    ("Coriander-Coconut Chutney", "South", "vegan", "dinner", "accompaniment", 30, 150, 3.2, 7.0, 12.5, 3.5),
    ("Mor (Spiced Buttermilk)", "South", "veg", "dinner", "accompaniment", 200, 35, 1.8, 4.0, 1.2, 0.0),
    # -- snacks & sweets --
    ("Medu Vada", "South", "vegan", "snack", "snack", 60, 245, 7.0, 26.0, 12.0, 3.5),
    ("Kozhukattai", "South", "vegan", "snack", "snack", 80, 215, 3.6, 40.0, 5.0, 2.0),
    ("Semiya Payasam", "South", "veg", "snack", "sweet", 120, 165, 3.5, 26.0, 5.0, 0.4),
    ("Mysore Pak", "South", "veg", "snack", "sweet", 40, 480, 6.0, 52.0, 27.0, 1.5),

    # =====================================================================
    # NORTH  -  Punjab, Haryana, UP, Delhi, Rajasthan
    # Wheat-led: roti/paratha/naan with a legume or paneer gravy, a dry
    # sabzi, and dairy accompaniments (kadhi, raita). Ghee/butter make many
    # signature dishes vegetarian rather than vegan, so plain dals, chana
    # preparations and oil-cooked sabzis carry the vegan coverage here.
    # =====================================================================
    # -- breakfast --
    ("Aloo Paratha", "North", "veg", "breakfast", "staple", 120, 245, 5.5, 36.0, 8.5, 3.2),
    ("Gobi Paratha", "North", "veg", "breakfast", "staple", 120, 235, 5.8, 33.0, 8.8, 3.8),
    ("Poori", "North", "vegan", "breakfast", "staple", 60, 340, 6.5, 45.0, 15.0, 2.6),
    ("Bhatura", "North", "veg", "breakfast", "staple", 80, 330, 7.0, 47.0, 13.0, 1.8),
    ("Besan Chilla", "North", "vegan", "breakfast", "staple", 100, 190, 9.0, 20.0, 8.0, 4.0),
    ("Poori-wale Aloo Sabzi", "North", "vegan", "breakfast", "side", 120, 115, 2.4, 15.0, 5.0, 2.2),
    ("Mint-Coriander Chutney", "North", "vegan", "breakfast", "accompaniment", 25, 85, 3.0, 10.0, 3.5, 3.5),
    # -- lunch staples --
    ("Roti (Whole Wheat)", "North", "vegan", "lunch", "staple", 40, 297, 11.0, 51.0, 7.5, 9.0),
    ("Missi Roti", "North", "vegan", "lunch", "staple", 50, 290, 11.5, 47.0, 6.5, 8.0),
    ("Jeera Rice", "North", "vegan", "lunch", "staple", 150, 165, 3.2, 32.0, 3.0, 1.0),
    # -- lunch mains --
    ("Rajma Masala", "North", "vegan", "lunch", "main", 150, 140, 7.0, 19.0, 3.5, 6.5),
    ("Chole (Chickpea Masala)", "North", "vegan", "lunch", "main", 150, 165, 8.0, 22.0, 5.0, 7.0),
    ("Kadhai Paneer", "North", "veg", "lunch", "main", 150, 215, 11.0, 8.0, 16.0, 2.0),
    ("Amritsari Fish Fry", "North", "nonveg", "lunch", "main", 130, 210, 18.0, 8.0, 12.0, 0.6),
    # -- lunch sides --
    ("Aloo Gobi", "North", "vegan", "lunch", "side", 120, 110, 2.8, 13.0, 5.5, 3.5),
    ("Jeera Aloo", "North", "vegan", "lunch", "side", 100, 135, 2.2, 19.0, 5.8, 2.4),
    ("Sarson ka Saag", "North", "veg", "lunch", "side", 150, 105, 4.0, 8.0, 6.5, 4.5),
    # -- lunch accompaniments --
    ("Punjabi Kadhi", "North", "veg", "lunch", "accompaniment", 150, 90, 3.5, 9.5, 4.2, 0.8),
    ("Boondi Raita", "North", "veg", "lunch", "accompaniment", 100, 95, 3.2, 8.0, 5.5, 0.5),
    ("Mango Pickle", "North", "vegan", "lunch", "accompaniment", 15, 195, 1.0, 12.0, 16.0, 2.5),
    ("Kachumber Salad", "North", "vegan", "lunch", "accompaniment", 60, 35, 1.2, 6.5, 0.4, 1.8),
    # -- dinner staples --
    ("Tandoori Roti", "North", "vegan", "dinner", "staple", 50, 285, 10.0, 53.0, 4.0, 8.0),
    ("Butter Naan", "North", "veg", "dinner", "staple", 70, 320, 8.5, 50.0, 9.5, 2.2),
    ("Veg Pulao", "North", "vegan", "dinner", "staple", 180, 170, 3.8, 29.0, 4.5, 2.0),
    ("Veg Biryani", "North", "veg", "dinner", "staple", 200, 175, 4.0, 26.0, 6.0, 2.2),
    ("Chicken Biryani", "North", "nonveg", "dinner", "staple", 200, 200, 11.0, 24.0, 7.0, 1.2),
    # -- dinner mains --
    ("Dal Tadka", "North", "vegan", "dinner", "main", 150, 120, 6.5, 15.0, 3.5, 4.5),
    ("Sabut Masoor Dal", "North", "vegan", "dinner", "main", 150, 118, 7.0, 15.0, 3.0, 5.0),
    ("Dal Makhani", "North", "veg", "dinner", "main", 150, 145, 6.5, 13.0, 7.5, 5.0),
    ("Paneer Butter Masala", "North", "veg", "dinner", "main", 150, 240, 9.0, 8.0, 19.0, 1.5),
    ("Palak Paneer", "North", "veg", "dinner", "main", 150, 155, 8.0, 6.0, 11.0, 2.8),
    ("Butter Chicken", "North", "nonveg", "dinner", "main", 150, 195, 15.0, 6.0, 12.0, 0.8),
    # -- dinner sides --
    ("Baingan Bharta", "North", "vegan", "dinner", "side", 120, 95, 2.2, 9.0, 5.5, 3.6),
    ("Gobi-Matar Sabzi", "North", "vegan", "dinner", "side", 120, 90, 3.4, 9.5, 4.2, 3.8),
    ("Methi Aloo", "North", "vegan", "dinner", "side", 100, 125, 3.0, 16.0, 5.5, 3.2),
    # -- dinner accompaniments --
    ("Cucumber Raita", "North", "veg", "dinner", "accompaniment", 100, 60, 2.8, 5.0, 3.2, 0.6),
    ("Green Chilli-Garlic Pickle", "North", "vegan", "dinner", "accompaniment", 12, 180, 3.0, 14.0, 13.0, 4.0),
    ("Sirke Wale Pyaaz (Pickled Onions)", "North", "vegan", "dinner", "accompaniment", 40, 45, 1.2, 9.0, 0.3, 1.6),
    # -- snacks & sweets --
    ("Paneer Tikka", "North", "veg", "snack", "snack", 120, 230, 14.0, 6.0, 17.0, 1.2),
    ("Samosa", "North", "vegan", "snack", "snack", 60, 300, 5.0, 34.0, 16.0, 2.8),
    ("Sweet Lassi", "North", "veg", "snack", "snack", 200, 95, 3.0, 14.0, 3.0, 0.0),
    ("Gajar Halwa", "North", "veg", "snack", "sweet", 100, 265, 4.0, 33.0, 13.0, 2.2),

    # =====================================================================
    # EAST  -  West Bengal, Odisha, Bihar, Jharkhand
    # Rice is the axis of every meal; courses run bitter -> dal -> vegetable
    # -> fish. Mustard oil and poppy seed dominate, so most vegetable and
    # dal preparations are vegan; the dairy shows up in the sweets.
    # =====================================================================
    # -- breakfast --
    ("Luchi", "East", "vegan", "breakfast", "staple", 50, 320, 6.0, 45.0, 13.0, 2.5),
    ("Radhaballavi (Dal Kachori)", "East", "vegan", "breakfast", "staple", 60, 330, 7.5, 43.0, 14.0, 3.0),
    ("Chirer Pulao (Flattened Rice)", "East", "veg", "breakfast", "staple", 180, 145, 3.0, 26.0, 3.4, 1.6),
    ("Pakhala Bhat (Fermented Rice)", "East", "vegan", "breakfast", "staple", 250, 88, 2.0, 19.0, 0.3, 0.5),
    ("Ghugni (Yellow Peas)", "East", "vegan", "breakfast", "main", 150, 140, 7.5, 20.0, 3.2, 6.0),
    ("Aloo Bhaja (Potato Fry)", "East", "vegan", "breakfast", "side", 80, 160, 2.0, 22.0, 7.5, 2.0),
    # -- lunch staples --
    ("Gobindobhog Bhaat (Steamed Rice)", "East", "vegan", "lunch", "staple", 150, 135, 2.8, 29.0, 0.4, 0.5),
    ("Bengali Khichuri", "East", "veg", "lunch", "staple", 200, 145, 5.5, 21.0, 4.5, 3.0),
    ("Litti (Sattu-stuffed)", "East", "vegan", "lunch", "staple", 100, 240, 8.0, 38.0, 6.0, 5.0),
    # -- lunch mains --
    ("Musur Dal (Red Lentil)", "East", "vegan", "lunch", "main", 150, 112, 7.0, 15.0, 2.5, 4.5),
    ("Dhokar Dalna", "East", "vegan", "lunch", "main", 150, 175, 8.0, 19.0, 7.5, 5.0),
    ("Cholar Dal", "East", "veg", "lunch", "main", 150, 150, 6.0, 20.0, 4.5, 5.5),
    ("Macher Jhol (Fish Curry)", "East", "nonveg", "lunch", "main", 150, 120, 13.0, 4.0, 6.0, 0.7),
    ("Kosha Mangsho (Mutton)", "East", "nonveg", "lunch", "main", 130, 235, 17.0, 5.0, 17.0, 0.8),
    # -- lunch sides --
    ("Aloo Posto", "East", "vegan", "lunch", "side", 120, 175, 4.0, 18.0, 9.0, 3.0),
    ("Begun Bhaja (Fried Aubergine)", "East", "vegan", "lunch", "side", 80, 145, 1.6, 10.0, 11.0, 3.0),
    ("Chokha (Mashed Brinjal-Potato)", "East", "vegan", "lunch", "side", 120, 85, 2.2, 12.0, 3.2, 3.0),
    # -- lunch accompaniments --
    ("Tomato-Khejur Chutney", "East", "vegan", "lunch", "accompaniment", 40, 150, 0.8, 36.0, 0.3, 1.2),
    ("Papad Bhaja (Fried Papad)", "East", "vegan", "lunch", "accompaniment", 15, 400, 19.0, 50.0, 14.0, 8.0),
    ("Doi (Set Curd)", "East", "veg", "lunch", "accompaniment", 100, 65, 3.2, 5.0, 3.4, 0.0),
    # -- dinner staples --
    ("Ruti (Atta Flatbread)", "East", "vegan", "dinner", "staple", 45, 290, 10.5, 52.0, 5.0, 8.5),
    ("Sattu Paratha", "East", "vegan", "dinner", "staple", 80, 285, 11.0, 44.0, 7.5, 7.0),
    ("Basanti Pulao", "East", "veg", "dinner", "staple", 180, 195, 3.6, 34.0, 5.2, 1.2),
    # -- dinner mains --
    ("Sona Moong Dal", "East", "vegan", "dinner", "main", 150, 128, 8.0, 17.0, 2.8, 5.0),
    ("Motor Dal (Split Pea)", "East", "vegan", "dinner", "main", 150, 125, 7.5, 17.0, 2.8, 5.0),
    ("Dimer Dalna (Bengali Egg Curry)", "East", "nonveg", "dinner", "main", 150, 165, 9.5, 8.0, 11.0, 1.2),
    ("Chingri Malai Curry (Prawn)", "East", "nonveg", "dinner", "main", 150, 185, 14.0, 6.0, 11.0, 0.6),
    ("Doi Maach (Fish in Yogurt)", "East", "nonveg", "dinner", "main", 150, 150, 14.5, 5.0, 8.0, 0.5),
    # -- dinner sides --
    ("Shukto", "East", "veg", "dinner", "side", 150, 95, 3.0, 12.0, 4.0, 4.0),
    ("Niramish Aloo Dum", "East", "vegan", "dinner", "side", 130, 140, 3.0, 20.0, 5.5, 3.0),
    ("Lau Ghonto (Bottle Gourd)", "East", "vegan", "dinner", "side", 130, 70, 1.8, 8.0, 3.5, 2.5),
    ("Palong Shaak Bhaja (Spinach)", "East", "vegan", "dinner", "side", 100, 85, 3.0, 6.0, 5.5, 3.0),
    # -- dinner accompaniments --
    ("Kasundi (Mustard Relish)", "East", "vegan", "dinner", "accompaniment", 15, 95, 4.0, 8.0, 5.0, 2.0),
    ("Aam Chutney (Green Mango)", "East", "vegan", "dinner", "accompaniment", 35, 130, 0.6, 31.0, 0.2, 1.0),
    ("Gondhoraj Ghol (Lime Buttermilk)", "East", "veg", "dinner", "accompaniment", 200, 30, 1.5, 3.5, 0.9, 0.0),
    # -- snacks & sweets --
    ("Beguni (Aubergine Fritter)", "East", "vegan", "snack", "snack", 50, 265, 5.5, 26.0, 15.0, 3.2),
    ("Muri Makha (Puffed Rice)", "East", "vegan", "snack", "snack", 60, 210, 5.0, 38.0, 4.5, 2.5),
    ("Sandesh", "East", "veg", "snack", "sweet", 50, 245, 9.0, 30.0, 9.0, 0.0),
    ("Mishti Doi", "East", "veg", "snack", "sweet", 100, 145, 4.0, 24.0, 3.5, 0.0),
    ("Rasgulla", "East", "veg", "snack", "sweet", 60, 186, 4.0, 38.0, 2.0, 0.0),

    # =====================================================================
    # WEST  -  Gujarat, Maharashtra, Goa, Konkan
    # Millet flatbreads (bajra, jowar) and rice both feature; Gujarat leans
    # sweet-savoury and vegetarian, coastal Maharashtra/Goa lean fish and
    # coconut. Groundnut oil is standard, so the vegan bench is deep.
    # =====================================================================
    # -- breakfast --
    ("Poha", "West", "vegan", "breakfast", "staple", 180, 130, 2.6, 25.0, 2.5, 1.2),
    ("Thepla", "West", "vegan", "breakfast", "staple", 60, 265, 7.0, 40.0, 8.5, 4.5),
    ("Sabudana Khichdi", "West", "vegan", "breakfast", "staple", 150, 230, 3.0, 38.0, 7.5, 1.5),
    ("Thalipeeth", "West", "vegan", "breakfast", "staple", 100, 215, 6.5, 34.0, 6.0, 5.0),
    ("Handvo", "West", "vegan", "breakfast", "staple", 120, 195, 7.0, 26.0, 7.0, 4.0),
    ("Misal Pav", "West", "vegan", "breakfast", "main", 220, 185, 7.5, 24.0, 6.5, 6.0),
    ("Gujarati Chhundo", "West", "vegan", "breakfast", "accompaniment", 25, 210, 0.5, 52.0, 0.2, 1.0),
    ("Green Garlic Chutney", "West", "vegan", "breakfast", "accompaniment", 20, 175, 5.0, 14.0, 11.0, 6.0),
    # -- lunch staples --
    ("Bajra Rotla", "West", "vegan", "lunch", "staple", 60, 295, 9.0, 55.0, 4.0, 9.0),
    ("Masala Bhaat", "West", "vegan", "lunch", "staple", 180, 180, 3.8, 30.0, 5.0, 2.2),
    ("Puran Poli", "West", "veg", "lunch", "staple", 90, 305, 7.0, 52.0, 7.5, 3.5),
    # -- lunch mains --
    ("Undhiyu", "West", "vegan", "lunch", "main", 180, 145, 4.5, 16.0, 7.5, 5.5),
    ("Gujarati Dal", "West", "vegan", "lunch", "main", 150, 110, 5.5, 17.0, 2.2, 4.0),
    ("Matki Usal (Sprouted Moth Bean)", "West", "vegan", "lunch", "main", 150, 135, 8.0, 18.0, 3.0, 6.5),
    ("Bombil Fry (Bombay Duck)", "West", "nonveg", "lunch", "main", 120, 165, 16.0, 6.0, 8.0, 0.4),
    ("Malvani Chicken Curry", "West", "nonveg", "lunch", "main", 150, 185, 17.0, 6.0, 10.0, 1.5),
    # -- lunch sides --
    ("Bhindi Masala", "West", "vegan", "lunch", "side", 120, 105, 2.5, 10.0, 6.0, 4.0),
    ("Sambharo (Cabbage-Carrot)", "West", "vegan", "lunch", "side", 100, 85, 1.8, 9.0, 4.5, 3.0),
    ("Batata Bhaji", "West", "vegan", "lunch", "side", 120, 120, 2.4, 18.0, 4.5, 2.2),
    # -- lunch accompaniments --
    ("Gujarati Kadhi", "West", "veg", "lunch", "accompaniment", 150, 85, 3.2, 9.0, 4.0, 0.6),
    ("Koshimbir (Cucumber-Peanut Salad)", "West", "vegan", "lunch", "accompaniment", 80, 90, 3.5, 7.0, 5.5, 2.5),
    ("Methia Keri Pickle", "West", "vegan", "lunch", "accompaniment", 15, 185, 2.0, 13.0, 14.0, 3.0),
    # -- dinner staples --
    ("Jowar Bhakri", "West", "vegan", "dinner", "staple", 60, 290, 8.5, 56.0, 3.2, 8.0),
    ("Pav (Bread Rolls)", "West", "vegan", "dinner", "staple", 50, 265, 8.0, 50.0, 3.5, 2.5),
    ("Gujarati Khichdi", "West", "veg", "dinner", "staple", 200, 140, 5.0, 22.0, 3.5, 3.0),
    # -- dinner mains --
    ("Vaal ni Dal (Field Beans)", "West", "vegan", "dinner", "main", 150, 135, 8.5, 18.0, 3.0, 6.0),
    ("Sev Tameta nu Shaak", "West", "vegan", "dinner", "main", 150, 165, 5.0, 18.0, 8.0, 3.0),
    ("Pav Bhaji", "West", "veg", "dinner", "main", 200, 145, 3.5, 18.0, 7.0, 4.2),
    ("Goan Fish Curry", "West", "nonveg", "dinner", "main", 150, 145, 13.0, 6.0, 8.0, 1.0),
    ("Kolhapuri Mutton Rassa", "West", "nonveg", "dinner", "main", 150, 215, 17.0, 5.0, 15.0, 1.0),
    # -- dinner sides --
    ("Ringna no Olo (Smoked Aubergine)", "West", "vegan", "dinner", "side", 120, 95, 2.0, 9.0, 5.5, 3.5),
    ("Tendli Bhaji (Ivy Gourd)", "West", "vegan", "dinner", "side", 100, 100, 2.0, 9.5, 6.0, 3.2),
    ("Gawar nu Shaak (Cluster Beans)", "West", "vegan", "dinner", "side", 100, 95, 3.2, 9.0, 4.8, 4.5),
    # -- dinner accompaniments --
    ("Sol Kadhi", "West", "vegan", "dinner", "accompaniment", 150, 65, 1.2, 7.0, 4.0, 0.8),
    ("Dry Garlic Chutney", "West", "vegan", "dinner", "accompaniment", 15, 480, 15.0, 26.0, 35.0, 8.0),
    ("Masala Chaas (Buttermilk)", "West", "veg", "dinner", "accompaniment", 200, 32, 1.6, 3.6, 1.0, 0.0),
    # -- snacks & sweets --
    ("Dhokla", "West", "vegan", "snack", "snack", 100, 160, 6.0, 24.0, 4.0, 3.0),
    ("Khaman", "West", "vegan", "snack", "snack", 100, 170, 7.0, 25.0, 4.5, 3.2),
    ("Batata Vada", "West", "vegan", "snack", "snack", 70, 240, 4.5, 30.0, 11.0, 2.8),
    ("Shrikhand", "West", "veg", "snack", "sweet", 100, 250, 6.0, 38.0, 8.0, 0.3),

    # =====================================================================
    # PAN-INDIA  -  eaten everywhere, returned alongside every region query.
    # These are the safety net that guarantees a plate can always be built:
    # plain rice/roti, a plain dal, an egg/chicken option, a mixed sabzi,
    # curd/salad/papad, and portable snacks.
    # =====================================================================
    ("Steamed Rice", "Pan-India", "vegan", "lunch", "staple", 150, 130, 2.7, 28.0, 0.3, 0.4),
    ("Multigrain Roti", "Pan-India", "vegan", "lunch", "staple", 45, 290, 10.0, 50.0, 6.5, 9.5),
    ("Chapati (Whole Wheat)", "Pan-India", "vegan", "dinner", "staple", 40, 297, 11.0, 51.0, 7.5, 9.0),
    ("Brown Rice", "Pan-India", "vegan", "dinner", "staple", 150, 123, 2.6, 25.6, 1.0, 1.8),
    ("Moong Dal", "Pan-India", "vegan", "lunch", "main", 150, 130, 8.0, 18.0, 2.0, 5.0),
    ("Masoor Dal", "Pan-India", "vegan", "dinner", "main", 150, 116, 7.2, 15.5, 2.5, 4.8),
    ("Grilled Chicken Tikka", "Pan-India", "nonveg", "lunch", "main", 120, 165, 25.0, 3.0, 6.0, 0.4),
    ("Chicken Curry", "Pan-India", "nonveg", "lunch", "main", 150, 175, 16.0, 5.0, 10.0, 1.0),
    ("Egg Curry", "Pan-India", "nonveg", "dinner", "main", 150, 160, 9.0, 6.0, 11.0, 1.0),
    ("Boiled Egg", "Pan-India", "nonveg", "breakfast", "main", 100, 155, 13.0, 1.1, 11.0, 0.0),
    ("Masala Omelette", "Pan-India", "nonveg", "breakfast", "main", 110, 175, 11.5, 2.5, 13.5, 0.5),
    ("Paneer Bhurji", "Pan-India", "veg", "breakfast", "main", 120, 215, 13.0, 5.0, 16.0, 1.0),
    ("Palak Sabzi (Stir-Fried Spinach)", "Pan-India", "vegan", "lunch", "side", 120, 80, 3.5, 5.0, 5.0, 2.8),
    ("Mixed Vegetable Sabzi", "Pan-India", "vegan", "dinner", "side", 150, 95, 3.0, 11.0, 4.5, 4.0),
    ("Green Salad", "Pan-India", "vegan", "lunch", "accompaniment", 100, 30, 1.2, 5.5, 0.3, 1.8),
    ("Curd (Plain Yogurt)", "Pan-India", "veg", "lunch", "accompaniment", 150, 60, 3.1, 4.7, 3.3, 0.0),
    ("Roasted Papad", "Pan-India", "vegan", "dinner", "accompaniment", 15, 350, 20.0, 55.0, 3.5, 9.0),
    ("Milk (Toned)", "Pan-India", "veg", "breakfast", "accompaniment", 200, 58, 3.1, 4.7, 3.0, 0.0),
    ("Banana", "Pan-India", "vegan", "snack", "snack", 120, 89, 1.1, 23.0, 0.3, 2.6),
    ("Apple", "Pan-India", "vegan", "snack", "snack", 150, 52, 0.3, 14.0, 0.2, 2.4),
    ("Papaya", "Pan-India", "vegan", "snack", "snack", 150, 43, 0.5, 11.0, 0.3, 1.7),
    ("Roasted Chana", "Pan-India", "vegan", "snack", "snack", 40, 364, 18.0, 51.0, 6.0, 18.0),
    ("Sprouts Salad", "Pan-India", "vegan", "snack", "snack", 100, 105, 8.0, 15.0, 1.0, 5.5),
    ("Almonds", "Pan-India", "vegan", "snack", "snack", 25, 600, 21.0, 21.0, 50.0, 12.0),
    ("Peanut Chikki", "Pan-India", "vegan", "snack", "sweet", 30, 470, 15.0, 55.0, 22.0, 5.0),
]

# Column order for DB insertion - must match the FOODS tuple order exactly.
COLUMNS = ["name", "region", "diet", "meal_slot", "role", "serving_g",
           "kcal", "protein_g", "carb_g", "fat_g", "fibre_g"]


# ---------------------------------------------------------------------------
# Food-preference cards
# ---------------------------------------------------------------------------
# Tap-to-pick ingredient/category cards shown on the "Food Preferences" screen.
# Each card maps to keywords used to match dishes in FOODS, so a user's likes
# and dislikes can bias (or filter) the generated meal plan. Emoji are used as
# zero-dependency, offline-friendly visuals (no image hosting required).
#
# Matching is a plain case-insensitive substring test against the dish name
# (see keywords_for + mealplan._matches), so the keyword lists carry both the
# English and the regional term for each category. A dish may legitimately
# match more than one card (Begun Bhaja is both "greens" and "fried").
FOOD_CARDS = [
    {"key": "paneer",  "label": "Paneer",         "emoji": "🧀",
     "keywords": ["paneer"]},
    {"key": "chicken", "label": "Chicken",        "emoji": "🍗",
     "keywords": ["chicken", "mangsho", "mutton", "rassa"]},
    {"key": "fish",    "label": "Fish & Seafood", "emoji": "🐟",
     "keywords": ["fish", "macher", "maach", "chingri", "bombil", "meen",
                  "moilee", "prawn"]},
    {"key": "egg",     "label": "Egg",            "emoji": "🥚",
     "keywords": ["egg", "omelette", "dimer"]},
    {"key": "rice",    "label": "Rice & Dosa",    "emoji": "🍚",
     "keywords": ["rice", "dosa", "idli", "pongal", "pakhala", "upma",
                  "bhaat", "biryani", "pulao", "khichdi", "khichuri",
                  "appam", "poha", "idiyappam", "muri"]},
    {"key": "wheat",   "label": "Roti & Wheat",   "emoji": "🫓",
     "keywords": ["roti", "paratha", "thepla", "luchi", "litti", "chapati",
                  "naan", "bhakri", "rotla", "poori", "bhatura", "ruti",
                  "thalipeeth", "poli", "pav", "chilla"]},
    {"key": "dal",     "label": "Dal & Legumes",  "emoji": "🫘",
     "keywords": ["dal", "rajma", "chole", "chana", "moong", "sambar",
                  "cholar", "paruppu", "kootu", "ghugni", "usal", "misal",
                  "masoor", "musur", "motor", "vaal", "matki", "sprout"]},
    {"key": "greens",  "label": "Leafy Greens",   "emoji": "🥬",
     "keywords": ["palak", "saag", "shukto", "sabzi", "undhiyu", "methi",
                  "shaak", "spinach", "keerai", "cabbage", "beans", "bhindi",
                  "gobi", "baingan", "brinjal", "aubergine", "tendli",
                  "gawar", "gourd", "poriyal", "thoran", "salad", "avial"]},
    {"key": "fruit",   "label": "Fruits",         "emoji": "🍌",
     "keywords": ["banana", "fruit", "apple", "papaya"]},
    {"key": "dairy",   "label": "Curd & Dairy",   "emoji": "🥛",
     "keywords": ["curd", "lassi", "yogurt", "kadhi", "sandesh", "doi",
                  "raita", "buttermilk", "chaas", "ghol", "milk",
                  "shrikhand", "payasam", "rasgulla"]},
    {"key": "nuts",    "label": "Nuts & Seeds",   "emoji": "🥜",
     "keywords": ["chana", "posto", "peanut", "almond", "cashew", "chikki",
                  "sattu", "coconut"]},
    {"key": "fried",   "label": "Fried Snacks",   "emoji": "🍟",
     "keywords": ["vada", "bhaji", "batata", "fry", "khaman", "pakora",
                  "luchi", "bhaja", "beguni", "samosa", "poori", "bhatura",
                  "kachori"]},
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
