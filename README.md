# Statistics Practice Generator

A local practice app for introductory statistics that uses Groq to generate problems and grade answers. Choose a topic, difficulty, and one to five problems in the Streamlit interface, reveal progressive hints, submit answers, and review worked solutions with a running score. A FastAPI backend validates generated data and keeps solutions in an in-memory cache until answers are checked. See [DESIGN.md](DESIGN.md) for the architecture and build plan.

## Setup

You need Git, Python 3.11 or newer, and a Groq API key. Run these commands in PowerShell:

```powershell
git clone https://github.com/CookieOreoYummy1/stats-practice-generator.git
cd stats-practice-generator
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace `GROQ_API_KEY` with your key:

```dotenv
GROQ_API_KEY=your_key_here
MODEL_NAME=openai/gpt-oss-120b
BACKEND_URL=http://localhost:8000
```

Both apps load the repository's `.env` automatically. Existing environment variables take precedence. `MODEL_NAME` selects the Groq model; the code falls back to `llama-3.3-70b-versatile` if it is unset. Keep `.env` private; it is excluded from Git. The backend checks credentials at startup, so it needs network access to Groq.

On macOS/Linux, use `python3 -m venv venv`, `source venv/bin/activate`, and `cp .env.example .env` in place of the corresponding PowerShell commands.

## Run

Both processes must stay running in **separate terminals**, with the repository as the working directory and the virtual environment activated in each.

Terminal 1 — backend:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.backend.main:app --reload --port 8000
```

Terminal 2 — frontend:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app/frontend/streamlit_app.py
```

Open **http://localhost:8501** for the practice app. Port **8000** serves the backend; interactive API documentation is at **http://localhost:8000/docs**. If activation is unavailable, use `venv\Scripts\python.exe -m uvicorn` or `venv\Scripts\python.exe -m streamlit` with the same arguments.

Choose a topic and click **Generate Problems**. Each **Next hint** click reveals one hint. **Check Answer** reveals feedback and the solution and counts that problem once in the score. **New Set** clears the current practice session. Restarting the backend clears its problem cache; select **New Set** if a previous problem can no longer be checked.

## Tests and demo checks

From the activated virtual environment:

```powershell
python -m pytest
```

The suite mocks external calls and covers request validation, provider configuration, retry handling, grading, math text formatting, hints, session resets, and readable frontend errors. It does not verify live model accuracy or browser-rendered LaTeX.

Medium confidence-interval exercises use structured numerical inputs. Python constructs the numerical question and calculates its standard error, interval bounds, and rounding, so the canonical answer and worked solution agree. The critical t value is explicitly supplied in the question; its table lookup is still model-provided. Other topics remain LLM-generated. Malformed math delimiters and LaTeX commands outside math delimiters trigger a generation retry.

Before a demo, generate problems across topics and difficulties, visually inspect the math, try correct and incorrect answers, reveal hints, and reset with **New Set**. Stop the backend briefly to check the connection-error message. Generation and grading require internet access; if a request fails, the app displays an error and preserves the current practice state.
