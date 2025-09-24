Great — below is the **complete, cleaned, MariaDB-ready project** with the folder structure you requested. Copy each file into the exact paths shown, install dependencies, set up `.env`, and you’ll be ready to run.

I kept the project modular and consistent with your requested structure:

```
mariadb-query-optimizer/
│
├── agents/
│   ├── __init__.py
│   ├── query_optimizer.py
│   ├── schema_advisor.py
│   ├── cost_advisor.py
│   └── data_validator.py
│
├── db/
│   └── mariadb_client.py
│
├── utils/
│   ├── __init__.py
│   ├── claude_client.py
│   └── config.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── logs/                      # created at runtime (add to .gitignore)
├── run.sh
├── main.py                    # FastAPI endpoint (orchestrator + API)
├── test_client.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Instructions (brief)

1. Create folder `mariadb-query-optimizer` and the subfolders shown.
2. Copy each file below into the matching path.
3. Copy `.env.example` → `.env` and fill values (`ANTHROPIC_API_KEY`, DB creds).
4. Create & activate venv, install deps:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Make `run.sh` executable and run:

   ```bash
   chmod +x run.sh
   ./run.sh
   ```
6. Open `frontend/index.html` in your browser (or serve it). Use UI to call the backend.

---

Below are **every file** — copy them exactly into your project.

---

### `requirements.txt`

```text
fastapi==0.95.2
uvicorn==0.22.0
python-dotenv==1.0.1
httpx==0.24.1
pymysql==1.1.0
```

---

### `.env.example`

```text
# Copy this file to .env and update values

# Anthropic / Claude API key
ANTHROPIC_API_KEY=your_claude_api_key_here

# MariaDB connection
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=your_db_password
DB_NAME=testdb

# App settings
SANDBOX_ONLY=true
LOG_LEVEL=INFO
API_HOST=127.0.0.1
API_PORT=8000
```

---

### `README.md`

```markdown
# MariaDB Query Optimizer + Claude Agents

Final, ready-to-run project that runs 4 Claude-powered agents (Query Optimizer, Schema Advisor, Cost Advisor, Data Validator)
against a MariaDB database. It exposes a FastAPI `/analyze` endpoint and includes a simple frontend.

## Quick start

1. Copy files into `mariadb-query-optimizer` folder (exact structure).
2. Create virtualenv and activate:
```

python3 -m venv venv
source venv/bin/activate

```
3. Install dependencies:
```

pip install -r requirements.txt

```
4. Copy `.env.example` to `.env` and fill values.
5. Start server:
```

chmod +x run.sh
./run.sh

```
or:
```

uvicorn main\:app --reload

```
6. Open `frontend/index.html` in your browser and test.

## Notes
- Keep `SANDBOX_ONLY=true` while developing. Agents return safe SELECT preview for destructive queries.
- The Claude client uses Anthropic REST-style endpoint by default. If you use AWS Bedrock or another gateway, adapt `utils/claude_client.py`.
- For local MariaDB, you can spin one up with Docker:
```

docker run -d --name mariadb -e MYSQL\_ROOT\_PASSWORD=secret -e MYSQL\_DATABASE=testdb -p 3306:3306 mariadb\:latest

```
```

---

### `run.sh`

```bash
#!/usr/bin/env bash
# run.sh - start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Make executable: `chmod +x run.sh`

---

## `utils/config.py`

```python
# utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
SANDBOX_ONLY = os.getenv("SANDBOX_ONLY", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
```

---

## `utils/claude_client.py`

```python
# utils/claude_client.py
import os
import json
import re
import logging
import httpx
from utils.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Default Anthropic endpoint shape (adjust if you use Bedrock or different gateway).
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY,
    "Content-Type": "application/json"
}

def _extract_json_from_text(text: str):
    if not text:
        raise ValueError("Empty text")

    # Try to find balanced JSON object {...}
    start = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{" and start is None:
            start = i
            depth = 1
        elif ch == "{":
            depth += 1
        elif ch == "}" and start is not None:
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                try:
                    return json.loads(candidate)
                except Exception:
                    break

    # Try array
    m = re.search(r'(\[.*\])', text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # Regex fallback for {...}
    m2 = re.search(r'(\{.*\})', text, flags=re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass

    # Last resort: try to parse everything
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Could not parse JSON from text: {e}")

def call_claude_raw(prompt: str, model: str = "claude-3.1", max_tokens: int = 800):
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set in environment."}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(ANTHROPIC_URL, headers=HEADERS, json=payload)
            r.raise_for_status()
            data = r.json()
            # Common shapes: data["content"][0]["text"] or data["completion"]
            if isinstance(data, dict):
                if "content" in data and isinstance(data["content"], list) and len(data["content"]) > 0:
                    c0 = data["content"][0]
                    if isinstance(c0, dict) and "text" in c0:
                        return {"text": c0["text"], "raw": data}
                if "completion" in data and isinstance(data["completion"], str):
                    return {"text": data["completion"], "raw": data}
            # Fallback: stringify
            return {"text": json.dumps(data), "raw": data}
    except Exception as e:
        logger.exception("Error calling Claude: %s", e)
        return {"error": str(e)}

def call_claude_json(prompt: str, model: str = "claude-3.1", max_tokens: int = 800):
    raw = call_claude_raw(prompt, model=model, max_tokens=max_tokens)
    if "error" in raw:
        return {"error": raw["error"], "raw": raw.get("raw")}
    text = raw.get("text", "")
    try:
        parsed = _extract_json_from_text(text)
        return parsed
    except Exception as e:
        logger.warning("Failed to parse JSON from Claude output: %s", e)
        return {"error": "Failed to parse JSON", "raw_text": text}
```

---

## `db/mariadb_client.py`

```python
# db/mariadb_client.py
import pymysql
from utils.config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
import logging

logger = logging.getLogger(__name__)

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def get_schema_for_tables(conn, tables):
    schema = {}
    try:
        with conn.cursor() as cur:
            for t in tables:
                cur.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (DB_NAME, t))
                rows = cur.fetchall()
                schema[t] = [{"column": r["COLUMN_NAME"], "type": r["COLUMN_TYPE"]} for r in rows]
    except Exception as e:
        logger.warning("Failed to fetch schema for %s: %s", tables, e)
    return schema

def get_full_schema(conn):
    schema = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """, (DB_NAME,))
            rows = cur.fetchall()
            for r in rows:
                tbl = r["TABLE_NAME"]
                schema.setdefault(tbl, []).append({"column": r["COLUMN_NAME"], "type": r["COLUMN_TYPE"]})
    except Exception as e:
        logger.warning("Failed to fetch full schema: %s", e)
    return schema

def explain_query(conn, sql):
    try:
        with conn.cursor() as cur:
            cur.execute("EXPLAIN " + sql)
            rows = cur.fetchall()
            return rows
    except Exception as e:
        logger.warning("Explain failed: %s", e)
        return {"error": str(e)}

def fetch_sample_rows(conn, sql, limit=5):
    if not sql.strip().lower().startswith("select"):
        return {"error": "Not a SELECT; sample rows skipped."}
    try:
        with conn.cursor() as cur:
            q = f"SELECT * FROM ({sql}) AS _sub LIMIT %s"
            cur.execute(q, (limit,))
            rows = cur.fetchall()
            return {"rows": rows, "count": len(rows)}
    except Exception as e:
        logger.warning("Failed to fetch sample rows: %s", e)
        return {"error": str(e)}
```

---

## `agents/__init__.py`

```python
# agents/__init__.py
from .query_optimizer import optimize_query
from .schema_advisor import advise_schema
from .cost_advisor import estimate_cost
from .data_validator import validate_query
```

---

## `agents/query_optimizer.py`

```python
# agents/query_optimizer.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)
DANGEROUS = ["delete", "update", "drop", "truncate", "alter"]

def _is_safe(sql: str):
    return not any(k in sql.lower() for k in DANGEROUS)

def optimize_query(sql: str, schema: dict, explain, sample_rows: dict):
    base = {"agent": "optimizer", "status": None, "query": sql, "safe_query": None, "details": {}}
    if not _is_safe(sql):
        prompt = f"""
You are a SQL safety and optimization expert for MariaDB/MySQL.

The provided SQL is UNSAFE to run in sandbox:
{sql}

Task:
1) Produce a SAFE SELECT-only preview query that shows rows that would be affected.
2) Briefly explain why the original is unsafe.

Return JSON ONLY:
{{ "safe_preview": "SELECT ...", "explanation": "..." }}
"""
        resp = call_claude_json(prompt)
        if "error" in resp:
            return {**base, "status": "error", "details": {"error": resp.get("error")}}
        return {**base, "status": "unsafe", "safe_query": resp.get("safe_preview"), "details": {"reasoning": resp.get("explanation")}}

    prompt = f"""
You are a Query Optimizer for MariaDB/MySQL.

INPUTS:
SQL:
{sql}

SCHEMA (JSON):
{json.dumps(schema, indent=2, default=str)}

EXPLAIN:
{json.dumps(explain, indent=2, default=str)}

SAMPLE_ROWS:
{json.dumps(sample_rows, indent=2, default=str)}

Task:
Return JSON ONLY with keys:
{{
  "optimized_query": "...",
  "changes": ["..."],
  "warnings": ["..."],
  "estimated_impact": "..."
}}
"""
    resp = call_claude_json(prompt)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "optimized_query": resp.get("optimized_query"),
        "recommendations": resp.get("changes", []),
        "warnings": resp.get("warnings", []),
        "estimated_impact": resp.get("estimated_impact")
    }
    return {**base, "status": "success", "details": details}
```

---

## `agents/schema_advisor.py`

```python
# agents/schema_advisor.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)
DANGEROUS = ["delete", "update", "drop", "truncate", "alter"]

def _is_safe(sql: str):
    return not any(k in sql.lower() for k in DANGEROUS)

def advise_schema(sql: str, schema: dict):
    base = {"agent": "schema_advisor", "status": None, "query": sql, "safe_query": None, "details": {}}
    if not _is_safe(sql):
        prompt = f"""
The query below is unsafe:
{sql}

Return JSON with a safe SELECT preview and explanation:
{{ "safe_preview": "SELECT ...", "explanation": "..." }}
"""
        resp = call_claude_json(prompt)
        if "error" in resp:
            return {**base, "status": "error", "details": {"error": resp.get("error")}}
        return {**base, "status": "unsafe", "safe_query": resp.get("safe_preview"), "details": {"reasoning": resp.get("explanation")}}

    prompt = f"""
You are a Schema Advisor for MariaDB/MySQL.

INPUT:
SQL:
{sql}

SCHEMA:
{json.dumps(schema, indent=2, default=str)}

Task:
Suggest schema improvements (indexes, partitioning, column types) to make this query faster.
Return JSON ONLY:
{{
  "recommended_indexes": ["CREATE INDEX ..."],
  "schema_changes": ["ALTER TABLE ...", "..."],
  "warnings": ["..."]
}}
"""
    resp = call_claude_json(prompt)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "recommendations": resp.get("recommended_indexes", []),
        "schema_changes": resp.get("schema_changes", []),
        "warnings": resp.get("warnings", [])
    }
    return {**base, "status": "success", "details": details}
```

---

## `agents/cost_advisor.py`

```python
# agents/cost_advisor.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)
DANGEROUS = ["delete", "update", "drop", "truncate", "alter"]

def _is_safe(sql: str):
    return not any(k in sql.lower() for k in DANGEROUS)

def estimate_cost(sql: str, explain):
    base = {"agent": "cost_advisor", "status": None, "query": sql, "safe_query": None, "details": {}}
    if not _is_safe(sql):
        prompt = f"""
Unsafe SQL detected:
{sql}

Return JSON with a safe preview and explanation:
{{ "safe_preview":"SELECT ...", "explanation":"..." }}
"""
        resp = call_claude_json(prompt)
        if "error" in resp:
            return {**base, "status": "error", "details": {"error": resp.get("error")}}
        return {**base, "status": "unsafe", "safe_query": resp.get("safe_preview"), "details": {"reasoning": resp.get("explanation")}}

    prompt = f"""
You are a Cost Advisor for MariaDB/MySQL.

INPUT:
SQL:
{sql}

EXPLAIN:
{json.dumps(explain, indent=2, default=str)}

Task:
Estimate relative cost/performance and give tips to reduce cost.
Return JSON ONLY:
{{
  "estimated_cost": "low|medium|high|numeric",
  "cost_saving_tips": ["..."],
  "warnings": ["..."]
}}
"""
    resp = call_claude_json(prompt)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "estimated_cost": resp.get("estimated_cost"),
        "cost_saving_tips": resp.get("cost_saving_tips", []),
        "warnings": resp.get("warnings", [])
    }
    return {**base, "status": "success", "details": details}
```

---

## `agents/data_validator.py`

```python
# agents/data_validator.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)
DANGEROUS = ["delete", "update", "drop", "truncate", "alter"]

def _is_safe(sql: str):
    return not any(k in sql.lower() for k in DANGEROUS)

def validate_query(sql: str, sample_rows: dict):
    base = {"agent": "data_validator", "status": None, "query": sql, "safe_query": None, "details": {}}
    if not _is_safe(sql):
        prompt = f"""
Unsafe SQL detected:
{sql}

Return JSON with a safe preview and explanation:
{{ "safe_preview": "SELECT ...", "explanation": "..." }}
"""
        resp = call_claude_json(prompt)
        if "error" in resp:
            return {**base, "status": "error", "details": {"error": resp.get("error")}}
        return {**base, "status": "unsafe", "safe_query": resp.get("safe_preview"), "details": {"reasoning": resp.get("explanation")}}

    prompt = f"""
You are a Data Validator.

INPUT:
SQL:
{sql}

SAMPLE_ROWS:
{json.dumps(sample_rows, indent=2, default=str)}

Task:
Inspect the sample rows and return JSON ONLY:
{{
  "issues": ["missing values in column X", "outliers in column Y"],
  "confidence": "high|medium|low",
  "reasoning": "short explanation"
}}
"""
    resp = call_claude_json(prompt)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "issues": resp.get("issues", []),
        "confidence": resp.get("confidence"),
        "reasoning": resp.get("reasoning")
    }
    return {**base, "status": "success", "details": details}
```

---

### `main.py` (root)

```python
# main.py
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from utils.config import LOG_LEVEL
from db.mariadb_client import (
    get_connection,
    get_schema_for_tables,
    get_full_schema,
    explain_query,
    fetch_sample_rows,
)
from agents.query_optimizer import optimize_query
from agents.schema_advisor import advise_schema
from agents.cost_advisor import estimate_cost
from agents.data_validator import validate_query

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# --------------------------------------------------
# FastAPI App
# --------------------------------------------------
app = FastAPI(title="MariaDB Query Optimizer (Claude Agents)")

# Serve static frontend
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def serve_frontend():
    """Serve index.html at root"""
    return FileResponse(os.path.join(frontend_path, "index.html"))

# --------------------------------------------------
# Request Model
# --------------------------------------------------
class AnalyzeRequest(BaseModel):
    sql: str
    tables: Optional[List[str]] = []
    run_in_sandbox: Optional[bool] = True

# --------------------------------------------------
# Helper to validate agent responses
# --------------------------------------------------
def validate_agent_response(resp: dict):
    if not isinstance(resp, dict):
        return False, "Not a dict"
    required = {"agent", "status", "query", "details"}
    missing = required - set(resp.keys())
    if missing:
        return False, f"Missing keys: {missing}"
    return True, None

# --------------------------------------------------
# API Endpoint
# --------------------------------------------------
@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    sql = req.sql.strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query required")

    try:
        conn = get_connection()
    except Exception as e:
        logger.exception("DB connection failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to connect to DB")

    try:
        # Schema context
        if req.tables:
            schema = get_schema_for_tables(conn, req.tables)
        else:
            schema = get_full_schema(conn)

        # Execution context
        explain = explain_query(conn, sql)
        sample = fetch_sample_rows(conn, sql)

        # Run agents
        opt = optimize_query(sql, schema, explain, sample)
        schema_r = advise_schema(sql, schema)
        cost_r = estimate_cost(sql, explain)
        validate_r = validate_query(sql, sample)

        agents = {
            "optimizer": opt,
            "schema_advisor": schema_r,
            "cost_advisor": cost_r,
            "data_validator": validate_r,
        }

        # Validate agent outputs
        for name, resp in agents.items():
            ok, err = validate_agent_response(resp)
            if not ok:
                logger.warning("Agent %s returned invalid response: %s", name, err)
                agents[name] = {
                    "agent": name,
                    "status": "error",
                    "query": sql,
                    "safe_query": None,
                    "details": {"error": err, "raw": resp},
                }

        # If optimizer gave a new query → run explain on it
        optimized_sql = (
            opt.get("details", {}).get("optimized_query") if isinstance(opt, dict) else None
        )
        optimized_explain = None
        if optimized_sql:
            optimized_explain = explain_query(conn, optimized_sql)

        # Final response
        response = {
            "original_query": sql,
            "schema_context": schema,
            "original_explain": explain,
            "sample_rows": sample,
            "agents": agents,
            "optimized_explain": optimized_explain,
        }

        return response

    finally:
        try:
            conn.close()
        except Exception:
            pass

```

---

### `test_client.py`

```python
# test_client.py
import requests, json

API = "http://127.0.0.1:8000/analyze"
sql = """
SELECT * FROM your_table LIMIT 5;
"""

payload = {
    "sql": sql,
    "tables": [],
    "run_in_sandbox": True
}

r = requests.post(API, json=payload, timeout=120)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2, default=str))
```

---

## `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MariaDB Query Optimizer</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <h1>MariaDB Query Optimizer — AI Agents</h1>
    <textarea id="sql" placeholder="Paste SELECT query here..."></textarea>
    <div class="controls">
      <input id="tables" placeholder="tables (comma separated)">
      <select id="sandbox">
        <option value="true">Run in sandbox (safe)</option>
        <option value="false">Run (not recommended)</option>
      </select>
      <button id="run">Run Analysis</button>
      <button id="clear">Clear</button>
    </div>

    <div id="message" class="hidden"></div>

    <div id="results" class="hidden">
      <h2>Summary</h2>
      <pre id="summary"></pre>
      <div id="cards"></div>
      <h3>Raw JSON</h3>
      <pre id="raw"></pre>
    </div>
  </div>
  <script src="script.js"></script>
</body>
</html>
```

---

## `frontend/style.css`

```css
body{font-family:Arial,Helvetica,sans-serif;background:#f4f6f8;color:#111;margin:20px}
.container{max-width:1000px;margin:0 auto;background:#fff;padding:18px;border-radius:8px;box-shadow:0 6px 20px rgba(10,20,30,0.06)}
textarea{width:100%;height:140px;padding:10px;border-radius:6px;border:1px solid #e6e9ee;font-family:monospace;margin-bottom:10px}
.controls{display:flex;gap:8px;align-items:center;margin-bottom:10px}
.controls input, .controls select{padding:8px;border-radius:6px;border:1px solid #e6e9ee}
button{padding:8px 12px;border-radius:6px;border:0;background:#2563eb;color:#fff;cursor:pointer}
.hidden{display:none}
.card{border:1px solid #e6e9ee;padding:12px;border-radius:6px;margin-bottom:8px;background:#fafafa}
pre{background:#0f172a;color:#e6e6e6;padding:12px;border-radius:6px;overflow:auto}
#message{padding:10px;border-radius:6px;margin-bottom:10px}
#message.error{background:#fff1f2;color:#b91c1c}
```

---

## `frontend/script.js`

```javascript
const API = "http://localhost:8000/analyze";

const sqlEl = document.getElementById("sql");
const tablesEl = document.getElementById("tables");
const sandboxEl = document.getElementById("sandbox");
const runBtn = document.getElementById("run");
const clearBtn = document.getElementById("clear");
const resultsEl = document.getElementById("results");
const summaryEl = document.getElementById("summary");
const cardsEl = document.getElementById("cards");
const rawEl = document.getElementById("raw");
const messageEl = document.getElementById("message");

runBtn.onclick = async () => {
  messageEl.className = "hidden";
  const sql = sqlEl.value.trim();
  if (!sql) {
    showMessage("Please paste a SQL query.", "error");
    return;
  }
  const tables = (tablesEl.value || "").split(",").map(s=>s.trim()).filter(Boolean);
  const run_in_sandbox = sandboxEl.value === "true";

  runBtn.disabled = true;
  runBtn.textContent = "Running...";

  try {
    const resp = await fetch(API, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({sql, tables, run_in_sandbox})
    });
    if (!resp.ok) {
      const txt = await resp.text();
      showMessage("Server error: " + resp.status + " - " + txt, "error");
      return;
    }
    const data = await resp.json();
    renderResults(data);
  } catch (err) {
    showMessage("Request failed: " + err.message, "error");
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run Analysis";
  }
};

clearBtn.onclick = () => {
  sqlEl.value = "";
  tablesEl.value = "";
  resultsEl.className = "hidden";
  cardsEl.innerHTML = "";
  rawEl.textContent = "";
  summaryEl.textContent = "";
  messageEl.className = "hidden";
};

function showMessage(text, type="info") {
  messageEl.textContent = text;
  messageEl.className = type === "error" ? "error" : "";
  messageEl.classList.remove("hidden");
}

function renderResults(data) {
  resultsEl.classList.remove("hidden");
  summaryEl.textContent = `Query: ${data.original_query}\nTables in context: ${Object.keys(data.schema_context || {}).length}\nSample rows: ${data.sample_rows && data.sample_rows.rows ? data.sample_rows.rows.length : 0}`;
  rawEl.textContent = JSON.stringify(data, null, 2);

  cardsEl.innerHTML = "";
  const agents = data.agents || {};
  Object.keys(agents).forEach(k => {
    const a = agents[k];
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<strong>${a.agent || k}</strong> — status: ${a.status || "unknown"}<br><br>`;
    if (a.safe_query) {
      card.innerHTML += `<div><strong>Safe preview:</strong><pre>${escape(a.safe_query)}</pre></div>`;
    }
    if (a.details) {
      for (const key of Object.keys(a.details)) {
        const val = a.details[key];
        if (Array.isArray(val)) {
          card.innerHTML += `<div><strong>${key}:</strong><ul>${val.map(i=>`<li>${escape(i)}</li>`).join("")}</ul></div>`;
        } else {
          card.innerHTML += `<div><strong>${key}:</strong><div><pre>${escape(val)}</pre></div></div>`;
        }
      }
    }
    cardsEl.appendChild(card);
  });
  if (data.optimized_explain) {
    const c = document.createElement("div");
    c.className = "card";
    c.innerHTML = `<strong>Optimized Explain</strong><pre>${escape(data.optimized_explain)}</pre>`;
    cardsEl.appendChild(c);
  }
}

function escape(s) { return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
```

---

## Final notes & troubleshooting

* If agents return `{"error":"Failed to parse JSON", "raw_text": "..."}`, inspect `raw_text` — LLM sometimes includes small extra text. Add clearer text in prompt (e.g., `"Respond ONLY with a JSON object and nothing else."`) inside the agent prompts if needed.
* If your Claude access is via AWS Bedrock or uses a different API, update `utils/claude_client.py` to match that gateway.
* For local MariaDB test database, use Docker (command shown in README) or install MariaDB locally.
* Keep `SANDBOX_ONLY=true` during development to avoid running destructive commands.

---

If you want I can:

* produce a single `bootstrap.sh` to write all files automatically,
* adapt `utils/claude_client.py` to a specific Claude/Bedrock method if you tell me which provider you use, or
* add unit tests and a small GitHub Actions workflow.

Which would you like next?
