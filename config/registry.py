# register.py
from config.base import Base
from users.models import User, UserRole, BalanceTransaction, BalanceTransactionType, VerificationCode
from driver.models import Driver, TruckType, DriverVerificationStatus
from order.models import Order, OrderWaypoint, OrderRoutePostGIS, OrderStatus, WaypointType, WaypointStatus
from Admin_panel.models import PlatformSettings

# Barcha modellarni SQLAlchemy ro'yxatidan o'tkazish (Registry) kafolati
__all__ = [
    "Base",
    "User", "UserRole", "BalanceTransaction", "BalanceTransactionType", "VerificationCode",
    "Driver", "TruckType", "DriverVerificationStatus",
    "Order", "OrderWaypoint", "OrderRoutePostGIS", "OrderStatus", "WaypointType", "WaypointStatus",
    "PlatformSettings",
]