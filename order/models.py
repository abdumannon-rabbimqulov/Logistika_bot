import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base


class OrderStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=True)

    cargo_name: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)

    from_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    to_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    distance_km: Mapped[float] = mapped_column(Numeric(7, 2), nullable=True)

    required_truck_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)

    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")

    pickup_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    delivery_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))

    customer = relationship("User", foreign_keys=[customer_id], backref="customer_orders")
    driver = relationship("Driver", foreign_keys=[driver_id], backref="driver_orders")
    truck_type = relationship("TruckType")

    # ✅ FIX 2: "Offer" → "OrderOffer" (to'g'ri model nomi)
    offers: Mapped[list["OrderOffer"]] = relationship("OrderOffer", back_populates="order")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, cargo='{self.cargo_name}', status={self.status})>"


class OfferStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderOffer(Base):
    __tablename__ = "order_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=False)

    offered_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    estimated_arrival_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), nullable=True)

    status: Mapped[OfferStatus] = mapped_column(
        SQLEnum(OfferStatus), default=OfferStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("Order", back_populates="offers")
    driver = relationship("Driver", back_populates="offers")

    def __repr__(self) -> str:
        return f"<Offer(id={self.id}, price={self.offered_price}, status={self.status})>"

