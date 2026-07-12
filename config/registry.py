from config.base import Base
from users.models import User, UserRole, UserTariffPayment, VerificationCode
from driver.models import Driver, TruckType, DriverVerificationStatus
from order.models import Order, OrderWaypoint, OrderRoutePostGIS, OrderStatus, WaypointType, WaypointStatus

# This file consolidates all models and Base to avoid circular imports.
# It should be imported by migrations/env.py and config/main.py.
