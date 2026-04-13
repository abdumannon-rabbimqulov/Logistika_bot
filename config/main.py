from fastapi import FastAPI
from config.config import engine,Base

app = FastAPI(title="FastAPI")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
