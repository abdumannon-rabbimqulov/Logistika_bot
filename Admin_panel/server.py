from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import database as db
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
async def get_stats():
    """Boshqaruv paneli uchun umumiy statistika."""
    try:
        stats = await db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def get_users(limit: int = 100):
    """Foydalanuvchilar ro'yxatini qaytaradi."""
    try:
        users = await db.get_all_users(limit=limit)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/ban")
async def ban_user(user_id: int):
    """Foydalanuvchini bloklash."""
    try:
        success = await db.ban_user(user_id)
        if success:
            return {"status": "success", "message": f"User {user_id} banned"}
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/unban")
async def unban_user(user_id: int):
    """Foydalanuvchi blokini ochish."""
    try:
        success = await db.unban_user(user_id)
        if success:
            return {"status": "success", "message": f"User {user_id} unbanned"}
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
