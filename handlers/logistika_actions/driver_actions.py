from database.db import db
import logging

async def set_driver_status_action(user_id: int, status: bool):
    """
    Sets the driver's availability status (online/offline).
    """
    try:
        # First check if user is a driver
        user = await db.get_user(user_id)
        if not user or user.role != 'driver':
            return {"status": "error", "message": "Siz haydovchi sifatida ro'yxatdan o'tmagansiz."}
            
        await db.set_online_status(user_id, status)
        status_text = "Online" if status else "Offline"
        return {"status": "success", "message": f"Sizning holatingiz {status_text} ga o'zgartirildi."}
    except Exception as e:
        logging.error(f"Error in set_driver_status_action: {e}")
        return {"status": "error", "message": str(e)}

async def search_available_orders_action():
    """
    Searches for available orders for drivers.
    """
    try:
        orders = await db.get_available_orders()
        if not orders:
            return {"status": "success", "message": "Hozircha bo'sh buyurtmalar yo'q.", "orders": []}
            
        order_list = []
        for o in orders:
            order_list.append({
                "id": o.id,
                "from": o.from_city,
                "to": o.to_city,
                "cargo": o.cargo_name,
                "weight": float(o.weight),
                "price": float(o.price)
            })
        return {"status": "success", "orders": order_list}
    except Exception as e:
        logging.error(f"Error in search_available_orders_action: {e}")
        return {"status": "error", "message": str(e)}
