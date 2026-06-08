import asyncio
from order.schemas import OrderCreate, OrderWaypointCreate
from pydantic import ValidationError

try:
    data = {
        "cargo_name": "Qurilish mollari (sement)",
        "weight": 20.0,
        "volume": 30.0,
        "required_truck_type_id": 2,
        "price": 4500000,
        "currency": "UZS",
        "waypoints": [
            {
                "sequence": 1,
                "waypoint_type": "pickup",
                "address": "Toshkent, Sergeli sanoat zonasi",
                "latitude": 41.220394,
                "longitude": 69.350832,
                "contact_name": "Aziz",
                "contact_phone": "+998901112233",
            },
            {
                "sequence": 2,
                "waypoint_type": "delivery",
                "address": "Samarqand, Shahar markazi",
                "latitude": 39.6542,
                "longitude": 66.9597,
                "contact_name": "Jasur",
                "contact_phone": "+998934445566",
            },
        ]
    }
    order = OrderCreate(**data)
    print("Pydantic INCOMING parsing works!")
except ValidationError as e:
    print("Pydantic INCOMING parsing failed:", e)

