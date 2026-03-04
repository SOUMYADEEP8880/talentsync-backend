# TalentSync AI — Backend

Complete FastAPI backend for TalentSync AI. Handles authentication, resume parsing, AI scoring, Pinecone vector search, and recruiter bulk ranking.

---

## Project Structure

```
talentsync-backend/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── Procfile                 # Railway deployment
├── railway.json
├── .env.example             # Copy to .env and fill keys
│
├── core/
│   ├── config.py            # Settings (reads .env)
│   ├── database.py          # SQLite async engine + session
│   └── security.py          # JWT auth helpers
│
├── models/
│   ├── user.py              # User table
│   ├── job.py               # Job table
│   └── resume.py            # Resume + MatchResult tables
│
├── routers/
│   ├── auth.py              # POST /api/auth/signup, /login, /me
│   ├── jobs.py              # GET/POST/DELETE /api/jobs
│   ├── resumes.py           # POST /api/resumes/upload
│   ├── match.py             # POST /api/match/score, /discover
│   └── recruiter.py         # POST /api/recruiter/rank, /generate-jd
│
└── services/
    ├── parser.py            # PDF + DOCX text extraction
    ├── claude_ai.py         # All Anthropic API calls
    ├── vector_search.py     # Pinecone embed + search
    └── seed_data.py         # 12 sample jobs
```

---

## Local Setup (5 minutes)

### 1. Clone and install

```bash
git clone <your-repo>
cd talentsync-backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Open .env and fill in your API keys
```

You need:
- **ANTHROPIC_API_KEY** → https://console.anthropic.com/
- **PINECONE_API_KEY** → https://app.pinecone.io/ (create a free index named `talentsync-jobs`, dimension `1536`, metric `cosine`)
- **OPENAI_API_KEY** → https://platform.openai.com/api-keys (used only for embeddings)
- **SECRET_KEY** → run `python -c "import secrets; print(secrets.token_hex(32))"`

### 3. Run

```bash
uvicorn main:app --reload
```

API is live at: **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

### 4. Seed the database with sample jobs

```bash
curl -X POST http://localhost:8000/api/jobs/seed
```

This inserts 12 jobs into SQLite and indexes them in Pinecone.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Register (candidate or recruiter) |
| POST | `/api/auth/login` | Login → get JWT token |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/jobs/` | List all jobs |
| POST | `/api/jobs/` | Create job (recruiter only) |
| POST | `/api/jobs/seed` | Seed 12 sample jobs |
| POST | `/api/resumes/upload` | Upload + parse resume (PDF/DOCX) |
| GET | `/api/resumes/` | List my resumes |
| POST | `/api/match/score` | Score saved resume vs JD |
| POST | `/api/match/score-upload` | Score uploaded resume vs JD (no auth) |
| POST | `/api/match/discover` | Find best-fit jobs via Pinecone |
| POST | `/api/recruiter/rank` | Bulk rank uploaded resumes vs JD |
| POST | `/api/recruiter/generate-jd` | Generate a tailored JD from resume |

---

## Deploy to Railway

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "TalentSync AI backend"
git remote add origin https://github.com/YOUR_USERNAME/talentsync-backend.git
git push -u origin main
```

### Step 2 — Create Railway project
1. Go to **railway.app** → New Project → Deploy from GitHub
2. Select your repo
3. Railway auto-detects Python and uses the `Procfile`

### Step 3 — Add environment variables
In Railway dashboard → your service → **Variables**, add:
```
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=talentsync-jobs
OPENAI_API_KEY=sk-...
SECRET_KEY=<generated>
DEBUG=false
```

### Step 4 — Deploy
Railway auto-deploys on every push. Your API URL will be something like:
`https://talentsync-backend-production.up.railway.app`

---

## Connecting to the Frontend

In your React frontend, replace the direct Anthropic API call with:

```javascript
// Instead of calling Anthropic directly:
const res = await fetch("https://your-railway-url.up.railway.app/api/match/score-upload", {
  method: "POST",
  body: formData,   // { file: resumeFile, jd_text: jd }
});
const data = await res.json();
// data = { score, verdict, summary, matched_skills, missing_skills, gap_analysis }
```

This keeps your API keys secure on the server.

---

## Security Notes

- All API keys are server-side only — never exposed to the browser
- Resumes are stored in SQLite with user scoping (users can only access their own)
- Passwords are bcrypt-hashed
- JWT tokens expire after 7 days
- CORS is open (`*`) by default — restrict to your frontend URL in production
