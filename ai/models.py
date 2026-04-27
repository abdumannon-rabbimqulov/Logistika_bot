"""
Mukkammal Rating & Chat System — SQLAlchemy 2.0 Mapped Style
=============================================================
Mavjud modellar:  User, Driver, Order
Yangi modellar:   Chat, Message, Attachment, Rating,
                  AIAnalysis, AICommand + barcha Enum lar
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, Enum as SAEnum, JSON, BigInteger,
)
from sqlalchemy.orm import (
     Mapped, mapped_column, relationship
)
from sqlalchemy.sql import func


from users.models import User
from driver.models import Driver
from order.models import Order
from config.config import Base




class ChatCategory(str, enum.Enum):
    COMPLAINT    = "complaint"
    SUGGESTION   = "suggestion"
    CONVERSATION = "conversation"
    AI_COMMAND   = "ai_command"
    SUPPORT      = "support"


class ChatStatus(str, enum.Enum):
    OPEN      = "open"
    RESOLVED  = "resolved"
    PENDING   = "pending"
    ESCALATED = "escalated"


class MessageType(str, enum.Enum):
    TEXT     = "text"
    VOICE    = "voice"
    IMAGE    = "image"
    VIDEO    = "video"
    FILE     = "file"
    SYSTEM   = "system"
    AI_REPLY = "ai_reply"


class SenderType(str, enum.Enum):
    USER   = "user"
    DRIVER = "driver"
    AI     = "ai"
    SYSTEM = "system"


class AttachmentType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    FILE  = "file"


class RatingTarget(str, enum.Enum):
    USER   = "user"
    DRIVER = "driver"


class AIAnalysisType(str, enum.Enum):
    CHAT_REVIEW      = "chat_review"
    COMPLAINT_VERIFY = "complaint_verify"
    SENTIMENT        = "sentiment"
    RATING_VERIFY    = "rating_verify"


class AIVerdict(str, enum.Enum):
    VALID     = "valid"
    INVALID   = "invalid"
    PARTIAL   = "partial"
    UNCERTAIN = "uncertain"


class AICommandType(str, enum.Enum):
    FIND_ORDER      = "find_order"
    TRACK_ORDER     = "track_order"
    CANCEL_ORDER    = "cancel_order"
    GET_RATING      = "get_rating"
    GET_HISTORY     = "get_history"
    CONTACT_SUPPORT = "contact_support"
    CUSTOM          = "custom"


class AICommandStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"

# ═════════════════════════════════════════════
# CHAT — Suhbat sessiyasi
# ═════════════════════════════════════════════

class Chat(Base):
    __tablename__ = "chats"

    id        : Mapped[str]            = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    user_id   : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("users.id"),   nullable=True)
    driver_id : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("drivers.id"), nullable=True)
    order_id  : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("orders.id"),  nullable=True, unique=True)

    # Chat meta
    category  : Mapped[ChatCategory]   = mapped_column(SAEnum(ChatCategory), default=ChatCategory.CONVERSATION, nullable=False)
    status    : Mapped[ChatStatus]     = mapped_column(SAEnum(ChatStatus),   default=ChatStatus.OPEN,           nullable=False)
    title     : Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)



    created_at : Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    closed_at  : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user        : Mapped[Optional["User"]]       = relationship(back_populates="chats")
    driver      : Mapped[Optional["Driver"]]     = relationship(back_populates="chats")
    order       : Mapped[Optional["Order"]]      = relationship(back_populates="chat")
    messages    : Mapped[list["Message"]]        = relationship(
                        back_populates="chat",
                        cascade="all, delete-orphan",
                        order_by="Message.created_at",
                        lazy="select")
    ai_analysis : Mapped[Optional["AIAnalysis"]] = relationship(back_populates="chat", uselist=False)


# ═════════════════════════════════════════════
# MESSAGE — Bitta xabar
# ═════════════════════════════════════════════

class Message(Base):
    __tablename__ = "messages"

    id           : Mapped[str]           = mapped_column(Integer, primary_key=True, )
    chat_id      : Mapped[str]           = mapped_column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)

    sender_id    : Mapped[Optional[str]] = mapped_column(Integer, nullable=True)
    sender_type  : Mapped[SenderType]    = mapped_column(SAEnum(SenderType),  nullable=False)
    message_type : Mapped[MessageType]   = mapped_column(SAEnum(MessageType), default=MessageType.TEXT, nullable=False)

    content        : Mapped[Optional[str]] = mapped_column(Text,    nullable=True)
    is_read        : Mapped[bool]          = mapped_column(Boolean, default=False)
    is_ai_response : Mapped[bool]          = mapped_column(Boolean, default=False)
    is_ai_command  : Mapped[bool]          = mapped_column(Boolean, default=False)

    # AI tahlil (xabar darajasida)
    ai_sentiment   : Mapped[Optional[float]] = mapped_column(Float,      nullable=True)
    ai_flagged     : Mapped[bool]            = mapped_column(Boolean,     default=False)
    ai_flag_reason : Mapped[Optional[str]]   = mapped_column(String(255), nullable=True)

    created_at : Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    edited_at  : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    chat        : Mapped["Chat"]                = relationship(back_populates="messages")
    attachments : Mapped[list["Attachment"]]    = relationship(
                        back_populates="message",
                        cascade="all, delete-orphan",
                        lazy="select")
    ai_command  : Mapped[Optional["AICommand"]] = relationship(back_populates="message", uselist=False)


# ═════════════════════════════════════════════
# ATTACHMENT — Rasm / Video / Ovoz / Fayl
# ═════════════════════════════════════════════

class Attachment(Base):
    __tablename__ = "attachments"

    id             : Mapped[str]            = mapped_column(Integer, primary_key=True, )
    message_id     : Mapped[str]            = mapped_column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)

    file_type      : Mapped[AttachmentType] = mapped_column(SAEnum(AttachmentType), nullable=False)
    file_url       : Mapped[str]            = mapped_column(String(512), nullable=False)
    original_name  : Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    mime_type      : Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    file_size      : Mapped[Optional[int]]  = mapped_column(BigInteger,  nullable=True)

    # Rasm / Video
    thumbnail_url  : Mapped[Optional[str]]  = mapped_column(String(512), nullable=True)
    width          : Mapped[Optional[int]]  = mapped_column(Integer,     nullable=True)
    height         : Mapped[Optional[int]]  = mapped_column(Integer,     nullable=True)

    # Ovoz (voice message)
    duration_sec   : Mapped[Optional[int]]  = mapped_column(Integer,  nullable=True)
    transcript     : Mapped[Optional[str]]  = mapped_column(Text,     nullable=True)
    transcript_lang: Mapped[str]            = mapped_column(String(10), default="uz")

    created_at     : Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message : Mapped["Message"] = relationship(back_populates="attachments")


# ═════════════════════════════════════════════
# RATING — User ↔ Driver reyting
# ═════════════════════════════════════════════

class Rating(Base):
    __tablename__ = "ratings"

    id              : Mapped[str]            = mapped_column(Integer, primary_key=True, )
    order_id        : Mapped[str]            = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)

    # Kim baho berdi
    rated_by_user   : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("users.id"),   nullable=True)
    rated_by_driver : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("drivers.id"), nullable=True)

    # Kim baholandi
    target_type     : Mapped[RatingTarget]   = mapped_column(SAEnum(RatingTarget), nullable=False)
    target_user     : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("users.id"),   nullable=True)
    target_driver   : Mapped[Optional[str]]  = mapped_column(Integer, ForeignKey("drivers.id"), nullable=True)

    # Baho
    score           : Mapped[int]            = mapped_column(Integer, nullable=False)   # 1 – 5
    comment         : Mapped[Optional[str]]  = mapped_column(Text,    nullable=True)

    criteria_scores : Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # AI tekshiruvi
    ai_verified        : Mapped[bool]               = mapped_column(Boolean,           default=False)
    ai_sentiment_score : Mapped[Optional[float]]    = mapped_column(Float,             nullable=True)
    ai_verdict         : Mapped[Optional[AIVerdict]]= mapped_column(SAEnum(AIVerdict), nullable=True)
    ai_verdict_reason  : Mapped[Optional[str]]      = mapped_column(Text,              nullable=True)
    is_suspicious      : Mapped[bool]               = mapped_column(Boolean,           default=False)

    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order             : Mapped["Order"]              = relationship(back_populates="rating")
    rater_user        : Mapped[Optional["User"]]     = relationship(
                            foreign_keys=[rated_by_user],
                            back_populates="ratings_given")
    rater_driver      : Mapped[Optional["Driver"]]   = relationship(
                            foreign_keys=[rated_by_driver],
                            back_populates="ratings_given")
    target_user_obj   : Mapped[Optional["User"]]     = relationship(
                            foreign_keys=[target_user],
                            back_populates="ratings_received")
    target_driver_obj : Mapped[Optional["Driver"]]   = relationship(
                            foreign_keys=[target_driver],
                            back_populates="ratings_received")
    ai_analysis       : Mapped[Optional["AIAnalysis"]] = relationship(
                            back_populates="rating", uselist=False)


# ═════════════════════════════════════════════
# AI ANALYSIS — AI tahlil natijasi
# ═════════════════════════════════════════════

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id            : Mapped[str]                     = mapped_column(Integer, primary_key=True, )
    chat_id       : Mapped[Optional[str]]           = mapped_column(Integer, ForeignKey("chats.id"),   nullable=True, unique=True)
    rating_id     : Mapped[Optional[str]]           = mapped_column(Integer, ForeignKey("ratings.id"), nullable=True, unique=True)

    analysis_type : Mapped[AIAnalysisType]          = mapped_column(SAEnum(AIAnalysisType), nullable=False)
    model_used    : Mapped[str]                     = mapped_column(String(100), default="claude-sonnet-4-20250514")

    # Natijalar
    confidence      : Mapped[Optional[float]]       = mapped_column(Float,   nullable=True)
    summary         : Mapped[Optional[str]]         = mapped_column(Text,    nullable=True)
    detected_issues : Mapped[Optional[list]]        = mapped_column(JSON,    nullable=True)
    complaint_valid : Mapped[Optional[bool]]        = mapped_column(Boolean, nullable=True)
    sentiment_score : Mapped[Optional[float]]       = mapped_column(Float,   nullable=True)
    toxicity_score  : Mapped[Optional[float]]       = mapped_column(Float,   nullable=True)
    verdict         : Mapped[Optional[AIVerdict]]   = mapped_column(SAEnum(AIVerdict), nullable=True)
    recommendation  : Mapped[Optional[str]]         = mapped_column(Text,    nullable=True)

    raw_response    : Mapped[Optional[dict]]        = mapped_column(JSON, nullable=True)

    analyzed_at     : Mapped[datetime]              = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chat   : Mapped[Optional["Chat"]]   = relationship(back_populates="ai_analysis")
    rating : Mapped[Optional["Rating"]] = relationship(back_populates="ai_analysis")


# ═════════════════════════════════════════════
# AI COMMAND — Foydalanuvchi AI ga bergan buyruq
# ═════════════════════════════════════════════

class AICommand(Base):
    __tablename__ = "ai_commands"

    id           : Mapped[str]              = mapped_column(Integer, primary_key=True)
    message_id   : Mapped[Optional[str]]    = mapped_column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, unique=True)
    user_id      : Mapped[str]              = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    command_type : Mapped[AICommandType]    = mapped_column(SAEnum(AICommandType),    nullable=False)
    raw_input    : Mapped[Optional[str]]    = mapped_column(Text, nullable=True)

    # AI o'zi parse qiladi: {"location": "Chilonzor", "max_distance_km": 3}
    parameters   : Mapped[Optional[dict]]   = mapped_column(JSON, nullable=True)

    status       : Mapped[AICommandStatus]  = mapped_column(SAEnum(AICommandStatus), default=AICommandStatus.PENDING)
    result       : Mapped[Optional[dict]]   = mapped_column(JSON, nullable=True)
    error_msg    : Mapped[Optional[str]]    = mapped_column(Text, nullable=True)

    created_at   : Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at  : Mapped[Optional[datetime]]= mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    message : Mapped[Optional["Message"]] = relationship(back_populates="ai_command")
    user    : Mapped["User"]              = relationship(back_populates="ai_commands")