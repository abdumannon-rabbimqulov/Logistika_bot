from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
import database as db
from config.config import get_db
from driver.router import router as driver_router
import uvicorn
import os

app = FastAPI(title="Logistika Bot Admin Panel")

# Routerlarni ulash
app.include_router(driver_router, prefix="/api")

@app.get("/admin")
@app.get("/")
async def serve_admin_panel():
    """Admin panelning asosiy sahifasini qaytaradi."""
    from fastapi.responses import FileResponse
    return FileResponse("frontend/index.html")

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stats")
async def get_stats(session: AsyncSession = Depends(get_db)):
    """Boshqaruv paneli uchun umumiy statistika."""
    try:
        stats = await db.get_stats(session=session)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def get_users(limit: int = 100, session: AsyncSession = Depends(get_db)):
    """Foydalanuvchilar ro'yxatini qaytaradi."""
    try:
        users = await db.get_all_users(limit=limit, session=session)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/ban")
async def ban_user(user_id: int, session: AsyncSession = Depends(get_db)):
    """Foydalanuvchini bloklash."""
    try:
        success = await db.ban_user(user_id, session=session)
        if success:
            await session.commit()
            return {"status": "success", "message": f"User {user_id} banned"}
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/unban")
async def unban_user(user_id: int, session: AsyncSession = Depends(get_db)):
    """Foydalanuvchi blokini ochish."""
    try:
        success = await db.unban_user(user_id, session=session)
        if success:
            await session.commit()
            return {"status": "success", "message": f"User {user_id} unbanned"}
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
