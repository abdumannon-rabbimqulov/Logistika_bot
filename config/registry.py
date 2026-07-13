# register.py
from config.base import Base
from users.models import User, UserRole, UserTariffPayment, VerificationCode
from driver.models import Driver, TruckType, DriverVerificationStatus
from order.models import Order, OrderWaypoint, OrderRoutePostGIS, OrderStatus, WaypointType, WaypointStatus

# Barcha modellarni SQLAlchemy ro'yxatidan o'tkazish (Registry) kafolati
__all__ = [
    "Base",
    "User", "UserRole", "UserTariffPayment", "VerificationCode",
    "Driver", "TruckType", "DriverVerificationStatus",
    "Order", "OrderWaypoint", "OrderRoutePostGIS", "OrderStatus", "WaypointType", "WaypointStatus"
]