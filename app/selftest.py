"""End-to-end smoke test for the NutriMind AI API.

Run the server first (uvicorn app.main:app --port 8000), then:
    python -m app.selftest
Exercises auth -> profile -> goal -> preferences -> plan -> recipe -> tracker
-> review and prints a PASS/FAIL line for each step.
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def call(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    passed = failed = 0

    def check(name, cond, extra=""):
        nonlocal passed, failed
        ok = bool(cond)
        passed += ok
        failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {extra}")

    s, h = call("GET", "/api/health")
    check("health", s == 200 and h.get("status") == "ok",
          f"(ai_mode={h.get('ai_mode')}, foods={h.get('foods')})")

    email = f"test_{int(time.time())}@example.com"
    s, d = call("POST", "/api/auth/register",
                {"name": "Test User", "email": email, "password": "secret123"})
    check("register", s == 200 and "token" in d)
    token = d.get("token")

    s, d = call("POST", "/api/auth/login",
                {"email": email, "password": "secret123"}, token)
    check("login", s == 200 and "token" in d)

    s, d = call("POST", "/api/auth/login",
                {"email": email, "password": "wrong"}, token)
    check("login rejects bad password", s == 401)

    s, d = call("POST", "/api/profile", {
        "dob": "1996-05-10", "sex": "male", "height_cm": 175, "weight_kg": 82,
        "activity": "moderate", "goal": "lose", "diet": "veg", "region": "South",
    }, token)
    check("save profile", s == 200 and d["metrics"]["bmi"] > 0,
          f"(BMI={d.get('metrics',{}).get('bmi')}, target={d.get('metrics',{}).get('target_calories')})")

    s, d = call("POST", "/api/suggest-goal", None, token)
    check("AI goal suggestion", s == 200 and d["suggestion"]["goal"] in
          ("lose", "maintain", "gain"),
          f"(goal={d.get('suggestion',{}).get('goal')}, src={d.get('suggestion',{}).get('source')})")

    s, d = call("POST", "/api/preferences",
                {"liked": ["dal", "rice"], "disliked": ["fried"]}, token)
    check("save preferences", s == 200 and d["ok"])

    s, d = call("POST", "/api/plan", {}, token)
    acc = d.get("plan", {}).get("calorie_accuracy_pct")
    check("meal plan", s == 200 and len(d["plan"]["meals"]) >= 3,
          f"(accuracy={acc}%, guidance_src={d.get('guidance',{}).get('source')})")

    s, d = call("POST", "/api/recipe",
                {"dish": "masala dosa", "servings": 2}, token)
    check("AI recipe", s == 200 and len(d["recipe"]["ingredients"]) > 0,
          f"(title={d.get('recipe',{}).get('title')!r}, src={d.get('recipe',{}).get('source')})")

    s, d = call("POST", "/api/log",
                {"note_text": "30 min run, ate dal and rice, skipped fried snacks"},
                token)
    check("tracker log + AI score", s == 200 and 1 <= d["ai"]["activity_score"] <= 10,
          f"(score={d.get('ai',{}).get('activity_score')}, src={d.get('ai',{}).get('source')})")

    s, d = call("POST", "/api/review",
                {"feature": "Meal Plan", "rating": 5, "comment": "Great!"}, token)
    check("review", s == 200 and d["ok"])

    s, d = call("GET", "/api/me", None, token)
    check("me aggregate", s == 200 and d["profile"] and d["tracker"]["count"] >= 1)

    s, d = call("GET", "/api/me", None, "bogus-token")
    check("auth rejects bad token", s == 401)

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
