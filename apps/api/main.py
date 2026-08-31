from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Uplift API",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}