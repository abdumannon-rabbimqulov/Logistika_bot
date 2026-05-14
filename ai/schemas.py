from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, List, Any, Literal
from enum import Enum



class ChatCategory(str, Enum):
    COMPLAINT    = "complaint"
    SUGGESTION   = "suggestion"
    CONVERSATION = "conversation"
    AI_COMMAND   = "ai_command"
    SUPPORT      = "support"

class ChatStatus(str, Enum):
    OPEN      = "open"
    RESOLVED  = "resolved"
    PENDING   = "pending"
    ESCALATED = "escalated"

class MessageType(str, Enum):
    TEXT     = "text"
    VOICE    = "voice"
    IMAGE    = "image"
    VIDEO    = "video"
    FILE     = "file"
    SYSTEM   = "system"
    AI_REPLY = "ai_reply"

class SenderType(str, Enum):
    USER   = "user"
    DRIVER = "driver"
    AI     = "ai"
    SYSTEM = "system"

class AttachmentType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    FILE  = "file"

class RatingTarget(str, Enum):
    USER   = "user"
    DRIVER = "driver"

class AIAnalysisType(str, Enum):
    CHAT_REVIEW      = "chat_review"
    COMPLAINT_VERIFY = "complaint_verify"
    SENTIMENT        = "sentiment"
    RATING_VERIFY    = "rating_verify"

class AIVerdict(str, Enum):
    VALID     = "valid"
    INVALID   = "invalid"
    PARTIAL   = "partial"
    UNCERTAIN = "uncertain"

class AICommandType(str, Enum):
    FIND_ORDER      = "find_order"
    TRACK_ORDER     = "track_order"
    CANCEL_ORDER    = "cancel_order"
    GET_RATING      = "get_rating"
    GET_HISTORY     = "get_history"
    CONTACT_SUPPORT = "contact_support"
    CUSTOM          = "custom"

class AICommandStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"

# --- Attachment Schemas ---

class AttachmentBase(BaseModel):
    file_type: AttachmentType = Field(...,)
    file_url: str = Field(..., max_length=512, )
    original_name: Optional[str] = Field(None, max_length=255,)
    mime_type: Optional[str] = Field(None, max_length=100, )
    file_size: Optional[int] = Field(None, )
    thumbnail_url: Optional[str] = Field(None, max_length=512)
    width: Optional[int] = Field(None, )
    height: Optional[int] = Field(None, )
    duration_sec: Optional[int] = Field(None,)
    transcript: Optional[str] = Field(None, )
    transcript_lang: str = "uz"

class AttachmentCreate(AttachmentBase):
    pass

class AttachmentResponse(AttachmentBase):
    id: int
    message_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Message Schemas ---

class MessageBase(BaseModel):
    sender_id: Optional[int] = Field(None,)
    sender_type: SenderType = Field(...,)
    message_type: MessageType = Field(MessageType.TEXT,)
    content: Optional[str] = Field(None, )
    is_read: bool = False
    is_ai_response: bool = False
    is_ai_command: bool = False

class MessageCreate(MessageBase):
    chat_id: int = Field(..., )
    attachments: Optional[List[AttachmentCreate]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chat_id": 10,
                "sender_id": 1,
                "sender_type": "user",
                "content": "Assalomu alaykum, yukni qachon olib ketasiz?",
                "message_type": "text"
            }
        }
    )

class MessageUpdate(BaseModel):
    is_read: Optional[bool] = None
    content: Optional[str] = None

class MessageResponse(MessageBase):
    id: int
    chat_id: int
    ai_sentiment: Optional[float] = Field(None, )
    ai_flagged: bool = False
    ai_flag_reason: Optional[str] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    attachments: List[AttachmentResponse] = []
    model_config = ConfigDict(from_attributes=True)

# --- Chat Schemas ---

class ChatBase(BaseModel):
    category: ChatCategory = Field(ChatCategory.CONVERSATION,)
    status: ChatStatus = Field(ChatStatus.OPEN,)
    title: Optional[str] = Field(None, max_length=255,)

class ChatCreate(ChatBase):
    user_id: Optional[int] = Field(None, )
    driver_id: Optional[int] = Field(None,)
    order_id: Optional[int] = Field(None, )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": "conversation",
                "title": "Haydovchi bilan suhbat",
                "user_id": 1,
                "driver_id": 2,
                "order_id": 50
            }
        }
    )

class ChatUpdate(BaseModel):
    status: Optional[ChatStatus] = None
    category: Optional[ChatCategory] = None
    closed_at: Optional[datetime] = None

class ChatResponse(ChatBase):
    id: int
    user_id: Optional[int]
    driver_id: Optional[int]
    order_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    closed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

# --- AIAnalysis Schemas ---

class AIAnalysisBase(BaseModel):
    analysis_type: AIAnalysisType = Field(...,)
    model_used: str = "gemini-flash-latest"
    confidence: Optional[float] = Field(None, )
    summary: Optional[str] = Field(None,)
    detected_issues: Optional[List[Any]] = None
    complaint_valid: Optional[bool] = None
    sentiment_score: Optional[float] = Field(None)
    toxicity_score: Optional[float] = Field(None)
    verdict: Optional[AIVerdict] = Field(None)
    recommendation: Optional[str] = Field(None)
    raw_response: Optional[dict] = None

class AIAnalysisCreate(AIAnalysisBase):
    chat_id: Optional[int] = None
    rating_id: Optional[int] = None

class AIAnalysisResponse(AIAnalysisBase):
    id: int
    chat_id: Optional[int]
    rating_id: Optional[int]
    analyzed_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- AICommand Schemas ---

class AICommandBase(BaseModel):
    command_type: AICommandType = Field(...,)
    raw_input: Optional[str] = Field(None, )
    parameters: Optional[dict] = Field(None,)

class AICommandCreate(AICommandBase):
    message_id: Optional[int] = None
    user_id: int = Field(..., )

class AICommandUpdate(BaseModel):
    status: Optional[AICommandStatus] = None
    result: Optional[dict] = None
    error_msg: Optional[str] = None
    executed_at: Optional[datetime] = None

class AICommandResponse(AICommandBase):
    id: int
    message_id: Optional[int]
    user_id: int
    status: AICommandStatus
    result: Optional[dict]
    error_msg: Optional[str]
    created_at: datetime
    executed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

# --- Rating Schemas ---

class RatingCriteria(BaseModel):
    scores: dict = Field(...,)

class RatingBase(BaseModel):
    order_id: int = Field(...,)
    target_type: RatingTarget = Field(...,)
    target_user: Optional[int] = None
    target_driver: Optional[int] = Field(None)
    score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, )
    criteria_scores: Optional[dict] = None

class RatingCreate(RatingBase):
    rated_by_user: Optional[int] = None
    rated_by_driver: Optional[int] = None

class RatingUpdate(BaseModel):
    comment: Optional[str] = None
    score: Optional[int] = Field(None, ge=1, le=5)

class RatingResponse(RatingBase):
    id: int
    rated_by_user: Optional[int]
    rated_by_driver: Optional[int]
    ai_verified: bool = True
    ai_sentiment_score: Optional[float] = Field(None, )
    ai_verdict: Optional[AIVerdict] = Field(None, )
    is_suspicious: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# WebSocket payloads (voice + AI)
# ─────────────────────────────────────────────────────────────


class VoiceMessageEvent(BaseModel):
    """WebSocket'ga `{type: voice_message}` bilan keladigan payload."""

    type: str = Field("voice_message")
    audio_b64: str = Field(..., description="base64-kodlangan audio bytes")
    mime_type: str = Field("audio/webm", description="audio/webm | audio/ogg | ...")
    sender_id: Optional[int] = None


# ─────────────────────────────────────────────────────────────
# Admin schemalar (model/limit/usage)
# ─────────────────────────────────────────────────────────────


class SetModelRequest(BaseModel):
    model_name: str = Field(..., min_length=2, max_length=100)


class CurrentModelResponse(BaseModel):
    model_name: str
    available: List[str]


class SetUserLimitRequest(BaseModel):
    daily_requests: int = Field(..., ge=0, le=10_000_000)


class SetUserTariffRequest(BaseModel):
    tariff: Literal["free", "pro"]


class UsageStatRow(BaseModel):
    user_id: int
    usage_date: date
    requests: int
    input_tokens: int
    output_tokens: int

    model_config = ConfigDict(from_attributes=True)


class UsageStatsResponse(BaseModel):
    items: List[UsageStatRow]
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
