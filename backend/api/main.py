from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.init import init_db
from backend.api.routes import researchers, works, analytics

app = FastAPI(title="UACJ SCI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
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
