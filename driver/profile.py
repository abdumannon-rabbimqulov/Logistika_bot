"""Haydovchi profil javobini yig'ish."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from driver import crud
from driver import schemas
from driver.models import Driver
from services import live_location
from users.models import User


async def build_driver_profile(
    db: AsyncSession,
    user: User,
    driver: Driver,
) -> schemas.DriverProfileResponse:
    truck_type = await crud.get_truck_type(db, driver.truck_type_id)
    live_payload = await live_location.get_driver_location(driver.id)

    gps_on = live_payload is not None or driver.is_gps_live
    gps_status = schemas.GpsStatus.ON if gps_on else schemas.GpsStatus.OFF

    if driver.is_blocked or not driver.is_available:
        user_status = schemas.UserStatus.OFFLINE
    elif gps_on or driver.is_live_location_active:
        user_status = schemas.UserStatus.LIVE
    else:
        user_status = schemas.UserStatus.OFFLINE

    balance_amount = Decimal(str(user.balance or 0))

    return schemas.DriverProfileResponse(
        id=driver.id,
        user_id=driver.user_id,
        name=user.full_name or user.username or "Haydovchi",
        rating=float(driver.rating or 0),
        balance=crud.format_balance_uzs(balance_amount),
        balance_amount=balance_amount,
        currency="UZS",
        user_status=user_status,
        gps_status=gps_status,
        phone_number=user.phone_number,
        truck_type_id=driver.truck_type_id,
        truck_type_name=truck_type.name if truck_type else None,
        truck_number=driver.truck_number,
        truck_year=driver.truck_year,
        current_city=driver.current_city,
        current_region=driver.current_region,
        is_available=driver.is_available,
        total_trips=driver.total_trips,
        on_time_percent=Decimal(str(driver.on_time_percent or 0)),
        is_blocked=driver.is_blocked,
    )
