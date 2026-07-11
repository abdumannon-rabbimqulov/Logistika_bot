from __future__ import annotations
import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey,
    SmallInteger, func, text, CheckConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from config.config import Base


class DriverVerificationStatus(enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"




class TruckType(Base):
    __tablename__ = "truck_types"

    id   : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # FIX: Numeric ustunlar endi Decimal deb annotatsiya qilingan (Numeric runtime'da Decimal qaytaradi, float emas)
    max_weight      : Mapped[Decimal]      = mapped_column(Numeric(6, 2), nullable=False)   # tonna
    max_volume      : Mapped[Decimal]      = mapped_column(Numeric(6, 2), nullable=False)   # m³
    length          : Mapped[Decimal|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    width           : Mapped[Decimal|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    height          : Mapped[Decimal|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    pallet_capacity : Mapped[int|None]     = mapped_column(Integer,       nullable=True)


    image_url   : Mapped[str|None]  = mapped_column(String(512), nullable=True)   # ikonka / rasm
    description : Mapped[str|None]  = mapped_column(String(200), nullable=True)
    is_active   : Mapped[bool]      = mapped_column(Boolean, default=True)
    # FIX: timezone=True — Driver modelidagi boshqa sana maydonlari bilan bir xillik uchun
    created_at  : Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    drivers : Mapped[list["Driver"]] = relationship("Driver", back_populates="truck_type_obj")

    def __repr__(self) -> str:
        return f"<TruckType(id={self.id}, name='{self.name}')>"



class Driver(Base):
    __tablename__ = "drivers"

    __table_args__ = (
        # FIX: DB darajasida rating chegarasini himoya qilish (Numeric(3,2) 9.99gacha joy beradi,
        # lekin biznes qoidasi bo'yicha rating 0-5 oralig'ida bo'lishi kerak)
        CheckConstraint("rating >= 0 AND rating <= 5", name="ck_drivers_rating_range"),
    )

    id      : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id : Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    truck_type_id  : Mapped[int]     = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)
    truck_number   : Mapped[str]     = mapped_column(String(20), unique=True, nullable=False)
    truck_year     : Mapped[int|None]= mapped_column(SmallInteger, nullable=True)

    current_city   : Mapped[str|None] = mapped_column(String(300))
    current_region : Mapped[str|None] = mapped_column(String(100))

    is_live_location_active  : Mapped[bool]          = mapped_column(Boolean,  default=False)
    # FIX: timezone=True — is_gps_live property'sidagi to_utc_naive/utc_now_naive "yamoqlari"
    # aslida shu yerdagi tz-naive ustunlar sababli kerak bo'lgan edi
    live_location_expires    : Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latitude             : Mapped[float|None]    = mapped_column(Float,    nullable=True)
    last_longitude            : Mapped[float|None]    = mapped_column(Float,    nullable=True)
    last_location_at          : Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    rating          : Mapped[Decimal] = mapped_column(Numeric(3, 2), default=5.0)
    total_trips     : Mapped[int]     = mapped_column(Integer, default=0)
    cancel_count    : Mapped[int]     = mapped_column(Integer, default=0)
    on_time_percent : Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100.0)

    is_available  : Mapped[bool] = mapped_column(Boolean, default=True)
    docs_verified : Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    # FIX: DriverVerificationStatus enum'i endi haqiqiy ustunga bog'landi.
    # docs_verified (bool) faqat "tasdiqlangan/yo'q" degan ikki holatni bilardi,
    # endi PENDING/APPROVED/REJECTED uch holatli jarayonni ham kuzatish mumkin
    verification_status: Mapped[DriverVerificationStatus] = mapped_column(
        SQLEnum(
            DriverVerificationStatus,
            name="driververificationstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DriverVerificationStatus.PENDING,
        nullable=False,
    )

    is_blocked    : Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason  : Mapped[str|None] = mapped_column(String(300), nullable=True)

    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user           = relationship("User", back_populates="driver")
    truck_type_obj : Mapped["TruckType"] = relationship("TruckType", back_populates="drivers")



    @property
    def is_gps_live(self) -> bool:
        """GPS hozir aktiv va muddati o'tmagan"""
        if not self.is_live_location_active:
            return False
        if self.live_location_expires:
            # FIX: ustunlar endi timezone-aware bo'lgani uchun to_utc_naive/utc_now_naive
            # "yamoqlariga" ehtiyoj qolmadi — to'g'ridan-to'g'ri aware datetime'lar solishtiriladi
            if datetime.now(timezone.utc) > self.live_location_expires:
                return False
        return True

    # FIX: @property -> hybrid_property. Bu bir xil kodni Python obyektida ham
    # ("driver.reliability_score"), SQL so'rovida ham ("order_by(Driver.reliability_score.desc())")
    # ishlatish imkonini beradi — masalan eng ishonchli haydovchini DB darajasida saralash uchun.
    @hybrid_property
    def reliability_score(self) -> float:
        """
        0-100 oralig'iga normallashtirilgan ishonchlilik bali.
        - rating (0-5)          -> 60 ball
        - on_time_percent (0-100) -> 30 ball
        - trip_bonus (tajriba)  -> +10 ballgacha bonus
        - cancel_penalty        -> bekor qilishlar uchun jarima (avval umuman hisobga olinmagan edi)
        """
        rating = float(self.rating or 0)
        on_time = float(self.on_time_percent or 0)
        trips = self.total_trips or 0
        cancels = self.cancel_count or 0

        rating_score = (rating / 5) * 60
        on_time_score = (on_time / 100) * 30
        trip_bonus = min(trips / 5, 10)
        # FIX: cancel_count endi jarima sifatida hisobga olinadi
        cancel_penalty = min(cancels * 3, 30)

        score = rating_score + on_time_score + trip_bonus - cancel_penalty
        return round(max(score, 0.0), 1)

    def __repr__(self) -> str:
        _id = self.__dict__.get("id", "Unknown")
        _truck = self.__dict__.get("truck_number", "Unknown")
        return f"<Driver(id={_id}, truck='{_truck}')>"