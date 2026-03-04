from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.database import init_db
from routers import auth, jobs, resumes, match, recruiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="TalentSync AI",
    description="AI-powered talent matching backend — resume parsing, semantic scoring, and job discovery.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(jobs.router,      prefix="/api/jobs",      tags=["Jobs"])
app.include_router(resumes.router,   prefix="/api/resumes",   tags=["Resumes"])
app.include_router(match.router,     prefix="/api/match",     tags=["Matching"])
app.include_router(recruiter.router, prefix="/api/recruiter", tags=["Recruiter"])


@app.get("/")
async def root():
    return {"status": "ok", "app": "TalentSync AI", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
