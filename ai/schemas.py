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
    file_type: AttachmentType
    file_url: str = Field(..., max_length=512)
    original_name: Optional[str] = Field(None, max_length=255)
    mime_type: Optional[str] = Field(None, max_length=100)
    file_size: Optional[int] = None
    thumbnail_url: Optional[str] = Field(None, max_length=512)
    width: Optional[int] = None
    height: Optional[int] = None
    duration_sec: Optional[int] = None
    transcript: Optional[str] = None
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
    sender_id: Optional[int] = None
    sender_type: SenderType
    message_type: MessageType = MessageType.TEXT
    content: Optional[str] = None
    is_read: bool = False
    is_ai_response: bool = False
    is_ai_command: bool = False

class MessageCreate(MessageBase):
    chat_id: int
    attachments: Optional[List[AttachmentCreate]] = None

class MessageUpdate(BaseModel):
    is_read: Optional[bool] = None
    content: Optional[str] = None

class MessageResponse(MessageBase):
    id: int
    chat_id: int
    ai_sentiment: Optional[float] = None
    ai_flagged: bool
    ai_flag_reason: Optional[str] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    attachments: List[AttachmentResponse] = []
    model_config = ConfigDict(from_attributes=True)

# --- Chat Schemas ---

class ChatBase(BaseModel):
    category: ChatCategory = ChatCategory.CONVERSATION
    status: ChatStatus = ChatStatus.OPEN
    title: Optional[str] = Field(None, max_length=255)

class ChatCreate(ChatBase):
    user_id: Optional[int] = None
    driver_id: Optional[int] = None
    order_id: Optional[int] = None

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
    analysis_type: AIAnalysisType
    model_used: str = "gemini-flash-latest"
    confidence: Optional[float] = None
    summary: Optional[str] = None
    detected_issues: Optional[List[Any]] = None
    complaint_valid: Optional[bool] = None
    sentiment_score: Optional[float] = None
    toxicity_score: Optional[float] = None
    verdict: Optional[AIVerdict] = None
    recommendation: Optional[str] = None
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
    command_type: AICommandType
    raw_input: Optional[str] = None
    parameters: Optional[dict] = None

class AICommandCreate(AICommandBase):
    message_id: Optional[int] = None
    user_id: int

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
    # Dynamic criteria, e.g., {"politeness": 5, "cleanliness": 4}
    scores: dict

class RatingBase(BaseModel):
    order_id: int
    target_type: RatingTarget
    target_user: Optional[int] = None
    target_driver: Optional[int] = None
    score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    criteria_scores: Optional[dict] = None

class RatingCreate(RatingBase):
    rated_by_user: Optional[int] = None
    rated_by_driver: Optional[int] = None

class RatingUpdate(BaseModel):
    comment: Optional[str] = None
    # Usually rating score is not updated, but we can allow it
    score: Optional[int] = Field(None, ge=1, le=5)

class RatingResponse(RatingBase):
    id: int
    rated_by_user: Optional[int]
    rated_by_driver: Optional[int]
    ai_verified: bool
    ai_sentiment_score: Optional[float]
    ai_verdict: Optional[AIVerdict]
    is_suspicious: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
