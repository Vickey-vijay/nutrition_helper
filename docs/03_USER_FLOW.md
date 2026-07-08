# NutriMind AI — User Flow

## 1. End-to-end user journey

```mermaid
flowchart TD
    Start([User opens NutriMind AI]) --> Auth{Has account?}
    Auth -- No --> Reg[Register: name, email, password]
    Auth -- Yes --> Login[Login: email, password]
    Reg --> Dash
    Login --> Dash[Dashboard]

    Dash --> HasProfile{Profile complete?}
    HasProfile -- No --> Profile[Complete profile:<br/>DOB, sex, height, weight,<br/>activity, diet, region]
    Profile --> AIgoal{Use AI goal suggestion?}
    AIgoal -- Yes --> Suggest[🤖 AI recommends<br/>lose / maintain / gain]
    AIgoal -- No --> ManualGoal[Pick goal manually]
    Suggest --> SaveP[Save & recalculate BMI/target]
    ManualGoal --> SaveP
    SaveP --> Dash

    HasProfile -- Yes --> Feature{Choose feature}
    Feature --> Plan[Meal Plan]
    Feature --> Pref[Food Preferences]
    Feature --> Recipe[Recipe Generator]
    Feature --> Track[Goal Tracker]
    Feature --> Review[Reviews]

    Pref --> PrefSave[Tap cards: like / avoid → Save]
    PrefSave --> Plan
    Plan --> Gen[Generate plan → table + AI guidance]
    Gen --> Regen{Regenerate?}
    Regen -- Yes --> Gen
    Regen -- No --> Feature

    Recipe --> Cook[Type dish + servings → AI recipe<br/>scaled to user's calorie budget]
    Cook --> Feature

    Track --> Log[Write daily note → AI summary + 1-10 score]
    Log --> Trend[View activity trend & history]
    Trend --> Feature

    Review --> Rate[Pick feature + stars + comment → Submit]
    Rate --> Feature

    Feature --> Logout([Logout])
```

## 2. Screen map

| Screen | Purpose | Primary API |
|--------|---------|-------------|
| Auth (Login/Register) | Account creation & sign-in | `/api/auth/*` |
| Dashboard | Snapshot: BMI, category, target, activity avg | `/api/me` |
| Profile | Biometrics + AI goal suggestion | `/api/profile`, `/api/suggest-goal` |
| Meal Plan | Day plan table + AI guidance | `/api/plan` |
| Food Preferences | Tap-to-pick like/avoid cards | `/api/food-cards`, `/api/preferences` |
| Recipe | Healthy recipe scaled to the user | `/api/recipe` |
| Goal Tracker | Daily note → AI score + trend | `/api/log`, `/api/logs` |
| Reviews | Feedback capture | `/api/review`, `/api/reviews` |

## 3. Preference card interaction

```mermaid
stateDiagram-v2
    [*] --> Neutral
    Neutral --> Like: tap
    Like --> Avoid: tap
    Avoid --> Neutral: tap
    note right of Like
        Liked categories are
        favoured in meal plans
    end note
    note right of Avoid
        Avoided categories are
        filtered out of meal plans
    end note
```

## 4. Authentication state

```mermaid
stateDiagram-v2
    [*] --> LoggedOut
    LoggedOut --> LoggedIn: register / login (token stored in localStorage)
    LoggedIn --> LoggedOut: logout (session deleted server-side)
    LoggedIn --> LoggedOut: 401 (expired/invalid token)
    LoggedIn --> LoggedIn: authenticated API calls (Bearer token)
```
