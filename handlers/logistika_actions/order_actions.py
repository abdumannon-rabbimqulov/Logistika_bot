from database.db import db
import logging

async def create_order_action(user_id: int, from_city: str, to_city: str, cargo_type: str, weight: float, price: float):
    """
    Creates a new logistics order.
    """
    try:
        data = {
            "cargo_type": cargo_type,
            "from_address": from_city,
            "to_address": to_city,
            "weight": weight,
            "price": price
        }
        order = await db.create_order(user_id, data)
        return {"status": "success", "order_id": order.id, "message": f"Buyurtma muvaffaqiyatli yaratildi (ID: {order.id})"}
    except Exception as e:
        logging.error(f"Error in create_order_action: {e}")
        return {"status": "error", "message": str(e)}

async def get_my_orders_action(user_id: int):
    """
    Returns list of orders created by the user.
    """
    try:
        orders = await db.get_user_orders(user_id)
        if not orders:
            return {"status": "success", "message": "Sizda hali buyurtmalar yo'q.", "orders": []}
        
        order_list = []
        for o in orders:
            order_list.append({
                "id": o.id,
                "from": o.from_city,
                "to": o.to_city,
                "cargo": o.cargo_name,
                "status": o.status.value,
                "price": float(o.price)
            })
        return {"status": "success", "orders": order_list}
    except Exception as e:
        logging.error(f"Error in get_my_orders_action: {e}")
        return {"status": "error", "message": str(e)}

async def cancel_order_action(user_id: int, order_id: int):
    """
    Cancels an existing order.
    """
    try:
        success = await db.cancel_order(order_id, user_id)
        if success:
            return {"status": "success", "message": f"Buyurtma #{order_id} bekor qilindi."}
        else:
            return {"status": "error", "message": "Buyurtma topilmadi yoki sizga tegishli emas."}
    except Exception as e:
        logging.error(f"Error in cancel_order_action: {e}")
        return {"status": "error", "message": str(e)}
