import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.init import init_db
from backend.api.routes import researchers, works, analytics

app = FastAPI(title="UACJ SCI API", version="0.1.0")

# Allowed origins: localhost for dev + Vercel production domain
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
    "https://uacj-sci.vercel.app",
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(researchers.router, prefix="/api")
app.include_router(works.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
