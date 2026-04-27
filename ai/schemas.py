from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum

# --- ENUM Schemas ---

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
    file_type: AttachmentType = Field(..., example=AttachmentType.IMAGE)
    file_url: str = Field(..., max_length=512, example="/static/uploads/photo_2024.jpg")
    original_name: Optional[str] = Field(None, max_length=255, example="yuk_holati.jpg")
    mime_type: Optional[str] = Field(None, max_length=100, example="image/jpeg")
    file_size: Optional[int] = Field(None, example=102400)
    thumbnail_url: Optional[str] = Field(None, max_length=512)
    width: Optional[int] = Field(None, example=1280)
    height: Optional[int] = Field(None, example=720)
    duration_sec: Optional[int] = Field(None, example=15)
    transcript: Optional[str] = Field(None, example="Salom, men yetib keldim")
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
    sender_id: Optional[int] = Field(None, example=1)
    sender_type: SenderType = Field(..., example=SenderType.USER)
    message_type: MessageType = Field(MessageType.TEXT, example=MessageType.TEXT)
    content: Optional[str] = Field(None, example="Salom, yuklarim tayyor")
    is_read: bool = False
    is_ai_response: bool = False
    is_ai_command: bool = False

class MessageCreate(MessageBase):
    chat_id: int = Field(..., example=10)
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
    ai_sentiment: Optional[float] = Field(None, example=0.85)
    ai_flagged: bool = False
    ai_flag_reason: Optional[str] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    attachments: List[AttachmentResponse] = []
    model_config = ConfigDict(from_attributes=True)

# --- Chat Schemas ---

class ChatBase(BaseModel):
    category: ChatCategory = Field(ChatCategory.CONVERSATION, example=ChatCategory.CONVERSATION)
    status: ChatStatus = Field(ChatStatus.OPEN, example=ChatStatus.OPEN)
    title: Optional[str] = Field(None, max_length=255, example="Toshkent-Andijon safari bo'yicha muloqot")

class ChatCreate(ChatBase):
    user_id: Optional[int] = Field(None, example=1)
    driver_id: Optional[int] = Field(None, example=2)
    order_id: Optional[int] = Field(None, example=100)

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
    analysis_type: AIAnalysisType = Field(..., example=AIAnalysisType.SENTIMENT)
    model_used: str = "gemini-flash-latest"
    confidence: Optional[float] = Field(None, example=0.98)
    summary: Optional[str] = Field(None, example="Foydalanuvchi suhbatdan mamnun")
    detected_issues: Optional[List[Any]] = None
    complaint_valid: Optional[bool] = None
    sentiment_score: Optional[float] = Field(None, example=0.9)
    toxicity_score: Optional[float] = Field(None, example=0.01)
    verdict: Optional[AIVerdict] = Field(None, example=AIVerdict.VALID)
    recommendation: Optional[str] = Field(None, example="Hech qanday chora ko'rish shart emas")
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
    command_type: AICommandType = Field(..., example=AICommandType.FIND_ORDER)
    raw_input: Optional[str] = Field(None, example="Menga Toshkentdagi yuklarni topib ber")
    parameters: Optional[dict] = Field(None, example={"city": "Toshkent"})

class AICommandCreate(AICommandBase):
    message_id: Optional[int] = None
    user_id: int = Field(..., example=1)

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
    scores: dict = Field(..., example={"xushmuomalalik": 5, "tezlik": 4})

class RatingBase(BaseModel):
    order_id: int = Field(..., example=50)
    target_type: RatingTarget = Field(..., example=RatingTarget.DRIVER)
    target_user: Optional[int] = None
    target_driver: Optional[int] = Field(None, example=2)
    score: int = Field(..., ge=1, le=5, example=5)
    comment: Optional[str] = Field(None, example="Juda yaxshi haydovchi, yukni vaqtida olib keldi")
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
    ai_sentiment_score: Optional[float] = Field(None, example=0.95)
    ai_verdict: Optional[AIVerdict] = Field(None, example=AIVerdict.VALID)
    is_suspicious: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
