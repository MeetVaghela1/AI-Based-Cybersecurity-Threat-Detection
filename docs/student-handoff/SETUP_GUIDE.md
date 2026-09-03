# Student Handoff — Setup Guide

This guide is for a student who has **never run a machine-learning project
before**. It takes you from an empty PC to a working dashboard that detects
cyber attacks in recorded network traffic.

What this guide covers, and nothing else:

1. What you are running (30-second version)
2. What to install first (the prerequisites)
3. Getting the project folder
4. One-time setup (the environment and dependencies)
5. Where the datasets live
6. Running the app — two modes
7. How to know it worked
8. If something goes wrong (troubleshooting)
9. The whole thing as one cheat-sheet

Your other two handoff documents cover what each screen means
(`PAGE_WALKTHROUGH.md`) and how the code is organised
(`CODE_AND_STRUCTURE_GUIDE.md`). You do not need them to get the app running.

---

## 1. What you are running (30-second version)

This project is a **cyber-threat detection demo**. It contains:

- four **machine-learning models** that have been trained to look at a single
  network connection (a "flow" — e.g. one computer sending another a web
  request) and decide: is this normal traffic, or an attack?
- a **website (dashboard)** that shows those models working. It replays
  recorded traffic one connection at a time and displays each verdict, plus
  charts that compare how good the four models are.
- the **research behind it**: two public datasets, four learning algorithms,
  and written reports explaining every decision.

Two software parts make this run:

| Part | What it is | Language | How it is started |
|---|---|---|---|
| **Backend** | Loads the trained models, does the classifying, feeds the website | Python | `uvicorn` server |
| **Frontend** | The website you look at in your browser | JavaScript (React) | Built with `npm`, then served by the backend |

You will start the backend with one command, open a browser, and see the
dashboard. Everything else is already prepared.

---

## 2. What to install first (the prerequisites)

You need three programs on the PC. The project has been tested with the
versions in bold, so use those if you can.

| Program | Tested version | Why you need it |
|---|---|---|
| **Python** | **3.12.10** | Runs the backend and the machine learning |
| **Node.js** (includes npm) | **Node v24.19.0**, npm **11.17.0** | Builds the website (frontend) |
| Git | any recent | Only needed if you clone the project from a repository. Optional. |

### 2.1 Check what is installed

Open a terminal (on Windows: press `Start`, type `PowerShell`, press Enter),
then run these three commands one at a time:

```powershell
python --version
node --version
npm --version
```

You should see output like:

```
Python 3.12.10
v24.19.0
11.17.0
```

> **Windows note:** if `python` is not found, try `py --version`, and use
> `py -3.12` in place of `python` everywhere below.

If any program is missing or too old, download it from the official site
(python.org for Python, nodejs.org for Node.js) and install it. After
installing, close and reopen the terminal so the programs are recognised.

---

## 3. Getting the project folder

The project was handed to you as a single folder named
`Cyber threat Detection` (it may arrive as a `.zip`).

1. If it is a zip, extract it somewhere easy to find, for example
   `C:\Cyber threat Detection` or your `Documents` folder.
   **Tip: avoid paths with unusual characters if you can — a simple path makes
   every command below easier.**
2. Open a terminal inside the project folder. In File Explorer, navigate into
   the folder, then click in the address bar, type `powershell`, and press
   Enter. A terminal opens with the project folder already selected.
3. Check you are in the right place — run:

```powershell
dir
```

You should see files like `README.md`, `SETUP_GUIDE.md`, `requirements.txt`,
and folders like `data`, `src`, `frontend`, `reports`, `tests`.

---

## 4. One-time setup (do this once, on the first run)

### 4.1 Create the Python "virtual environment"

A virtual environment is a private copy of Python inside the project folder,
so the packages you install here do not clash with other projects. Run:

```powershell
python -m venv .venv
```

This creates a `.venv` folder (it takes a few seconds). You will never need to
touch it.

### 4.2 Activate the environment

```powershell
.venv\Scripts\activate
```

After this, your terminal prompt starts with `(.venv)`. **That means you are
"inside" the environment — every Python command below must be run while this
prefix is showing.** If you close the terminal and come back, run this
activate command again first.

> If you use the classic Command Prompt instead of PowerShell, the command is
> `.venv\Scripts\activate.bat`.

### 4.3 Install the Python packages

Run:

```powershell
pip install -r requirements.txt
```

`requirements.txt` is a list of every Python library the project needs,
with pinned versions so your PC matches the machine it was built on. This step
can take several minutes and prints a lot of text — that is normal. Watch the
end of the output: it should say all packages were installed successfully.

Verify everything imported correctly:

```powershell
python -c "import pandas, numpy, sklearn, xgboost, imblearn, joblib, fastapi, uvicorn, pydantic, pytest; print('all imports OK')"
```

You want to see `all imports OK` with no red error text.

### 4.4 Install and build the website (frontend)

Still in the project folder:

```powershell
cd frontend
npm install
npm run build
cd ..
```

- `npm install` downloads the JavaScript packages the website needs
  (one time).
- `npm run build` turns the website source code into a finished, optimised
  version that the backend can serve. It prints a small summary ending with
  the name of the built file. This creates the `frontend/dist` folder.

If `npm` is not recognised, Node.js is not installed or not on your PATH
(re-read §2).

### 4.5 The datasets

Skip this section if the datasets were included with the project folder (they
usually are — see §5). If they are missing, §5 explains how to get them.

---

## 5. Where the datasets live

The models were trained on two public cyber-security datasets, stored in the
`data/raw` folder:

| Folder inside `data/raw` | Dataset | Files the pipeline actually uses |
|---|---|---|
| `nsl-kdd` | NSL-KDD | `KDDTrain+.txt` and `KDDTest+.txt` |
| `MachineLearningCSV\MachineLearningCVE` | CICIDS2017 | all 8 `*-WorkingHours*.csv` files |

`data/raw/DATASET_MANIFEST.md` lists every file with its size, row count, and
whether the pipeline uses it (`USED`) or keeps it only for record (`IGNORED`).
If the datasets did not come with the folder, download the two items above and
place them in those exact locations:

- NSL-KDD: the official `KDDTrain+.txt` (125,973 rows) and `KDDTest+.txt`
  (22,544 rows) from the NSL-KDD project page.
- CICIDS2017: the "ML-ready" CSV collection (79 columns per file, ~2.8
  million rows total) — the folder and files must match the names above.

The pipeline reads from `data/raw` **only**. A handful of leftover copies of
these datasets also sit at the project root (`nsl-kdd`, `MachineLearningCSV`,
`GeneratedLabelledFlows`) — those are unused backups from development and can
be ignored (or deleted to save ~4 GB).

---

## 6. Running the app — two modes

### Mode A — Fast start (recommended for the demo)

Use this when the folder already contains the trained models
(`src\models\registry`) and the cleaned data (`data\processed`) — i.e. a
normal handoff folder. You do **not** re-train anything; you just start the
server:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

Leave this terminal open. You should see a few lines of log output ending with
something like `Uvicorn running on http://127.0.0.1:8000`.

Now open your browser and go to **http://127.0.0.1:8000** — you will see the
"CyberGuard" dashboard. Press the **Start Monitoring** button and live-looking
traffic starts streaming past (it is a replay of recorded test data — the
dashboard shows a "SIMULATED TRAFFIC" badge to make this clear).

### Mode B — Retrain everything from scratch

Use this if the trained models or cleaned data are missing, or if you want to
prove the whole pipeline reproduces (this is what makes the thesis numbers
credible). This command reloads the raw data, re-cleans it, re-runs grid
search + cross-validation for all 8 models (4 algorithms × 2 datasets), and
saves everything back:

```powershell
.venv\Scripts\python.exe -m src.models.train
```

**How long it takes (real, measured times):**

| Dataset | Model | Grid combos | Fit time |
|---|---|---|---|
| NSL-KDD | Decision Tree | 9 | ~25 s |
| NSL-KDD | Logistic Regression | 4 | ~120 s |
| NSL-KDD | XGBoost | 8 | ~181 s |
| NSL-KDD | Random Forest | 8 | ~205 s |
| CICIDS2017 | Logistic Regression | 4 | ~67 s |
| CICIDS2017 | Decision Tree | 9 | ~28 s |
| CICIDS2017 | Random Forest | 8 | ~113 s |
| CICIDS2017 | XGBoost | 8 | ~195 s |

Total ≈ 30–45 minutes on a 16-core machine (more on a weaker one). Each
combination is validated with 5-fold cross-validation, which is why it is
slow. When it finishes it prints
`Retraining complete. Models live in src/models/registry/.`

Then start the server exactly as in Mode A. If the frontend was never built,
first run `cd frontend; npm run build; cd ..` (§4.4).

---

## 7. How to know it worked

The strongest check is visual: at http://127.0.0.1:8000 you should see the
dashboard and pressing **Start Monitoring** should produce predictions that
update every ~2 seconds.

If you want a text-only check, or if the page loads but looks broken:

1. **Backend responds.** Open http://127.0.0.1:8000/docs — FastAPI shows an
   interactive API documentation page listing every endpoint. If this page
   loads, the backend is running.
2. **Models are reachable.** In the browser visit
   http://127.0.0.1:8000/models. You should get JSON listing 8 models
   (4 per dataset) with their accuracy, precision, recall, F1 and AUC scores.
   If this returns an error instead, see §8 row 3.
3. **Try a prediction.** In PowerShell run:

```powershell
curl.exe -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d "{\"dataset\":\"cicids\",\"model\":\"xgboost\",\"row_id\":0}"
```

   You should get JSON back including `"prediction"` and `"confidence"`.

4. **Tests pass (recommended).** Run the project's own test suite:

```powershell
.venv\Scripts\python.exe -m pytest tests\ -q
```

   Expect **19 passed** (14 in `test_api.py` + 5 in `test_panel_api.py`). The
   warnings printed are harmless deprecation notices. This is the same suite
   the maintainer ran; if all 19 pass, the installation is healthy.

---

## 8. If something goes wrong (troubleshooting)

Work down the list — the most common causes are at the top.

| # | Symptom / error you see | What it means and what to do |
|---|---|---|
| 1 | `ModuleNotFoundError: No module named 'pandas'` (or any package) | The virtual environment is not activated or packages were never installed. Run `.venv\Scripts\activate`, then `pip install -r requirements.txt`. |
| 2 | `'python' is not recognized` | Python is not on your PATH. Try `py -3.12` instead of `python` (Windows), or reinstall Python and tick "Add to PATH". |
| 3 | Browser shows `"Evaluation results not found — run Phase 4 first."` (503) | The file `data\processed\evaluation_results.json` is missing, so the API cannot answer. The cleaned-data folder was left out of the handoff — run Mode B (§6) to regenerate it, or restore `data/processed` from the source machine. |
| 4 | `NSL-KDD file not found: ... KDDTrain+.txt` / `Check data/raw/DATASET_MANIFEST.md — the .txt files are required.` | The NSL-KDD `.txt` files are missing from `data/raw/nsl-kdd`. Download them (§5). This error is raised by `src/data/loader.py`. |
| 5 | `No CICIDS2017 CSV files found in ... matching '*-WorkingHours*.csv'` | The CICIDS2017 CSVs are missing from `data/raw/MachineLearningCSV\MachineLearningCVE`. Download them (§5). Raised by `src/data/loader.py`. |
| 6 | `models_metadata.json not found — train the models first.` (503) or `/models` returns an error / empty list | The trained models in `src\models\registry` are missing. Run Mode B (§6), which trains all 8 models and rebuilds `models_metadata.json`. |
| 7 | `405 Method Not Allowed` or the page looks like old code | The served website is stale. Rebuild it: `cd frontend; npm run build; cd ..`, then refresh the browser with `Ctrl+F5` (hard refresh, to bypass the browser cache). |
| 8 | Browser shows `"Frontend not built yet. Run: cd frontend && npm install && npm run build"` | The backend is running but `frontend/dist` does not exist. Do §4.4, then refresh. |
| 9 | `Address already in use` / port 8000 busy | Another program uses port 8000. Pick a different port, e.g. `.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8001`, and open http://127.0.0.1:8001. |
| 10 | `npm` is not recognized | Node.js is not installed or not on your PATH. Install Node (nodejs.org), close and reopen the terminal, then refresh PATH in PowerShell with: `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")` |
| 11 | Training is very slow / runs out of memory | Lower `n_jobs` in `src/models/train.py` (e.g. set `n_jobs=2` in `retrain_all(...)` and in the grid-search call) and retry Mode B. |
| 12 | `Unknown attack type '...'` (404) on the How-It-Works page | You are viewing an attack the backend does not explain. This only matters if the frontend and backend versions differ — rebuild the frontend (§4.4). |

If none of these match, run `python -m pytest tests\ -q` and note the first
failing test name — it tells you which part of the pipeline is unhappy.

---

## 9. The whole thing as one cheat-sheet

One-time setup (first run only):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

Every time you come back to the project:

```powershell
.venv\Scripts\activate
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

Then open **http://127.0.0.1:8000** and press **Start Monitoring**.

If something is broken or missing:

```powershell
.venv\Scripts\python.exe -m pytest tests\ -q      # check the install (expect 19 passed)
.venv\Scripts\python.exe -m src.models.train       # rebuild all 8 models (30-45 min)
```

That is the whole setup. For what each screen means, read
`PAGE_WALKTHROUGH.md`. For how the code is organised, read
`CODE_AND_STRUCTURE_GUIDE.md`.
