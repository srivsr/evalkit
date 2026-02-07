import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import init_db
from .routers import evaluate_router, projects_router, health_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="EvalKit API",
    description="RAG Evaluation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = settings.allowed_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(evaluate_router)
app.include_router(projects_router)
app.include_router(health_router)


@app.get("/")
async def root():
    return {"message": "EvalKit API v1.0.0", "docs": "/docs"}
