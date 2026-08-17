# NutriMind AI — Setup Guide

A step-by-step guide to get NutriMind AI running on a Windows computer. No coding
knowledge required.

> **In a hurry?** Install Python (below), then double-click **`start.bat`** —
> it installs everything and launches the app in one step. `setup.bat` +
> `run.bat` do the same thing as two separate steps.

## Before you start

You need **one thing** installed: **Python 3.10 or newer**.

1. Go to <https://www.python.org/downloads/> and download the latest Python 3 installer.
2. Run the installer. On the **first screen**, tick the box:
   ✅ **"Add python.exe to PATH"**
   (This is important — the setup script won't work without it.)
3. Click **Install Now** and let it finish.

That's it — no Node.js, no other tools needed.

## Step 1 — Download the project

1. Open the GitHub page you were sent.
2. Click the green **Code** button → **Download ZIP**.
3. Find the downloaded `.zip` file (usually in your **Downloads** folder) and
   **extract it** (right-click → "Extract All...").
4. Open the extracted folder.

## Step 2 — Run the setup

1. Double-click **`setup.bat`**.
2. A black command-prompt window opens and installs everything needed.
   It runs in two parts:
   - **Dependencies** — about 1–2 minutes.
   - **The local AI model** — a one-time download of roughly **4 GB**, which
     can take **10–40 minutes** depending on your connection. This is normal;
     leave the window running. On machines with under 8 GB of RAM a smaller
     ~2.4 GB model is chosen automatically.
3. When it says **"Setup complete"**, this step is done and never needs
   repeating.

> **The download is optional.** If it fails, you stop it, or you have no
> internet, setup still finishes and the app still works — it simply uses one
> of the other AI options in Step 3. To fetch the model later, run
> `.venv\Scripts\python.exe -m app.setup_model` from the project folder.

> If Windows shows a security pop-up ("Windows protected your PC"), click
> **More info → Run anyway**. This happens because the file was downloaded from
> the internet — it is safe, it only installs the app's own dependencies.

## Step 3 — (Optional) Choose how the AI runs

The app has three ways of producing its recipes, meal guidance and daily
summaries, and it picks the best one available on its own. **You do not have to
do anything here** — it works out of the box.

| Option | Speed | Needs | Notes |
|---|---|---|---|
| **Groq cloud** | ~1 second | a free key + internet | fastest; used first when available |
| **Local AI model** | 30 s – 4 min | the model from Step 2 | works completely offline, costs nothing |
| **Built-in fallback** | instant | nothing | always available; no setup at all |

To enable the fast cloud option:

1. In the project folder, open the **`.env`** file with Notepad.
2. Find the line `GROQ_API_KEY=` and paste your key right after the `=`, e.g.
   `GROQ_API_KEY=gsk_your_key_here`
3. Save the file and close Notepad.

(A free key can be created at <https://console.groq.com>.)

To force the app to run **fully offline** using only the local model, set
`NUTRIMIND_AI_BACKEND=local` in the same `.env` file. Answers then take longer,
but nothing leaves your computer.

## Step 4 — Run the app

1. Double-click **`run.bat`**.
2. A window will open and, after a few seconds, your browser will automatically
   open to **http://localhost:8000** with the app running.
3. To stop the app, close the black command-prompt window (or press `Ctrl+C` in it).

Next time you want to use the app, you only need **`run.bat`** — setup does not
need to be repeated unless you move the folder to a different computer.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Python was not found" | Reinstall Python and make sure "Add python.exe to PATH" is ticked. |
| Setup fails installing dependencies | Check your internet connection, then run `setup.bat` again. |
| Browser doesn't open automatically | Manually open your browser and go to `http://localhost:8000`. |
| "Port 8000 already in use" | The app is likely already running in another window — just use that one. |
| Antivirus flags the `.bat` files | This is a false positive — the scripts only run `pip install` and start the app. |

## What this app does

NutriMind AI is a region-aware, AI-assisted Indian diet-planning platform:
accounts & profiles, BMI/calorie calculation, AI-personalised meal plans, a
recipe generator, a daily goal tracker, and feedback capture. See
[`README.md`](README.md) for full technical details.
