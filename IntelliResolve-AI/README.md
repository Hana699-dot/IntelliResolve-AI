# IntelliResolve AI — Streamlit IT Service Desk

A one-day MVP demonstrating Generative AI-assisted IT service management:
- Natural-language IT support assistant
- Gemini-powered incident classification and priority suggestion
- Knowledge-base retrieval (lightweight local keyword retrieval)
- SQLite incident creation and lifecycle tracking
- Recurring incident pattern detection
- Admin dashboard and ticket analytics

## 1. Requirements
- Python 3.10+
- Gemini API key (optional; the app has a local demo fallback)

Get a Gemini API key: https://aistudio.google.com/apikey

## 2. Setup (Windows PowerShell)

```powershell
cd IntelliResolve-AI
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use:
```powershell
.venv\Scripts\activate.bat
```

## 3. Configure Gemini

Create `.streamlit/secrets.toml` and add:
```toml
GEMINI_API_KEY = "YOUR_REAL_API_KEY"
```

Do not commit this file or share your API key. If you skip this step, the app runs in demo mode with local rule-based classification and knowledge-base answers.

## 4. Run

```powershell
python -m streamlit run app.py
```

Open the local URL shown in the terminal, usually http://localhost:8501.

## 5. Demo flow for placement review

1. Open Overview and show seeded example incidents.
2. Open AI Support Assistant and enter:
   `I cannot connect to office Wi-Fi and I have an important meeting in 10 minutes.`
3. Show the detected category, priority and Network Support routing.
4. Create an incident from the conversation.
5. Open Manage Tickets and move it to In Progress or Resolved; add resolution notes.
6. Open Incident Intelligence to show repeated network reports.
7. Open Knowledge Base and search for Wi-Fi.

## 6. Architecture

Streamlit UI -> AI triage (Gemini) -> local knowledge retrieval -> SQLite incident store -> recurring-incident detector -> dashboard.

The current project simulates the ITSM workflow locally. It does **not** claim to connect to a live ServiceNow instance. A future integration can map ticket creation and updates to ServiceNow Incident APIs, with appropriate authentication and approval controls.

## 7. Important limitations

- The local knowledge retriever uses keyword overlap, not embedding-based semantic search. This keeps setup fast and avoids model downloads.
- Incident clustering is a basic category/keyword signal, not proof of a common root cause.
- Gemini output is advisory. Human support staff should verify priority, routing and resolutions.
- Do not enter real passwords, MFA codes, personal data or confidential company information.
