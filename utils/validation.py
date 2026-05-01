"""
🔒 INPUT VALIDATION & SECURITY UTILITIES

Bu modul turli input validation rules va security checks'ni o'z ichiga oladi.
"""

import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
from decimal import Decimal


class ValidationError(Exception):
    """Custom validation error."""
    pass


# ─────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ─────────────────────────────────────────────────────────────

PATTERNS = {
    # Phone numbers
    "phone_uzbekistan": r"^\+998([0-9]{2})[0-9]{7}$|^([0-9]{2})[0-9]{7}$",  # +998 or 0x format
    "phone_international": r"^\+?1?\d{9,15}$",  # General international format
    
    # Vehicle info
    "truck_plate_uzbekistan": r"^[0-9]{2}[A-Z]{1}[0-9]{3}[A-Z]{2}$",  # 60А123BC format
    "truck_plate_general": r"^[A-Z0-9]{2,20}$",  # General format
    
    # Cities (Cyrillic and Latin)
    "city_name": r"^[a-zA-Z\u0400-\u04FF\'\s\-]{2,100}$",  # Latin/Cyrillic + hyphens
    
    # Addresses
    "address": r"^[a-zA-Z0-9\u0400-\u04FF\'\s\-\.,\/]{3,300}$",
    
    # Names
    "person_name": r"^[a-zA-Z\u0400-\u04FF\'\s\-]{2,128}$",
}


# ─────────────────────────────────────────────────────────────
# VALIDATORS
# ─────────────────────────────────────────────────────────────

def validate_phone_number(value: Optional[str]) -> Optional[str]:
    """
    Phone number validate qilish.
    Supports: +998YYXXXXXXX, 0YYXXXXXXX, YYXXXXXXX
    """
    if not value:
        return None
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-\(\)]+', '', value)
    
    # Check format
    if not re.match(r"^\+998\d{9}$|^0\d{9}$|\d{9}$", cleaned):
        raise ValueError(f"❌ Invalid phone format: {value}")
    
    # Normalize to +998 format
    if cleaned.startswith("0"):
        cleaned = "+998" + cleaned[1:]
    elif not cleaned.startswith("+"):
        cleaned = "+998" + cleaned
    
    return cleaned


def validate_truck_plate(value: str) -> str:
    """
    Truck plate (davlat raqami) validate qilish.
    Format: 60А123BC yoki 60A123BC
    """
    if not value:
        raise ValueError("Truck plate required")
    
    # Remove spaces
    plate = value.upper().strip()
    
    # Check format (Uzbekistan: numbers + letter + numbers + letters)
    if not re.match(r"^[0-9]{2}[A-Z]{1}[0-9]{3}[A-Z]{2}$", plate):
        # Try general format if specific doesn't match
        if not re.match(r"^[A-Z0-9]{3,20}$", plate):
            raise ValueError(f"❌ Invalid truck plate format: {value}")
    
    return plate


def validate_city_name(value: str) -> str:
    """
    Shahar nomi validate qilish.
    Allows: Latin, Cyrillic, hyphens, apostrophes
    """
    if not value:
        raise ValueError("City name required")
    
    cleaned = value.strip()
    
    # Min/max length
    if len(cleaned) < 2 or len(cleaned) > 100:
        raise ValueError(f"❌ City name must be 2-100 characters: {value}")
    
    # Check characters
    if not re.match(PATTERNS["city_name"], cleaned):
        raise ValueError(f"❌ Invalid city name format: {value}")
    
    return cleaned


def validate_price(value: float, min_price: float = 0, max_price: float = 999999999.99) -> Decimal:
    """
    Narx validate qilish.
    Negative prices yo'q, max limit tekshirish.
    """
    try:
        price = Decimal(str(value))
    except:
        raise ValueError(f"❌ Invalid price format: {value}")
    
    if price < min_price:
        raise ValueError(f"❌ Price cannot be less than {min_price}")
    
    if price > max_price:
        raise ValueError(f"❌ Price cannot exceed {max_price}")
    
    return price


def validate_weight(value: float, min_weight: float = 0.1, max_weight: float = 100.0) -> float:
    """
    Yuk og'irligi validate qilish (tonna).
    Range: 0.1 - 100 tonna
    """
    try:
        weight = float(value)
    except:
        raise ValueError(f"❌ Invalid weight format: {value}")
    
    if weight <= 0:
        raise ValueError(f"❌ Weight must be positive")
    
    if weight < min_weight:
        raise ValueError(f"❌ Weight cannot be less than {min_weight} tons")
    
    if weight > max_weight:
        raise ValueError(f"❌ Weight cannot exceed {max_weight} tons")
    
    return weight


def validate_coordinates(latitude: float, longitude: float) -> tuple:
    """
    GPS koordinatalari validate qilish.
    Latitude: -90 to 90, Longitude: -180 to 180
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
    except:
        raise ValueError(f"❌ Invalid coordinates format")
    
    if not (-90 <= lat <= 90):
        raise ValueError(f"❌ Latitude must be between -90 and 90: {latitude}")
    
    if not (-180 <= lon <= 180):
        raise ValueError(f"❌ Longitude must be between -180 and 180: {longitude}")
    
    return (lat, lon)


def validate_distance(value: float, min_distance: float = 0.1, max_distance: float = 5000.0) -> float:
    """
    Masofa validate qilish (km).
    Range: 0.1 - 5000 km
    """
    try:
        distance = float(value)
    except:
        raise ValueError(f"❌ Invalid distance format: {value}")
    
    if distance <= 0:
        raise ValueError(f"❌ Distance must be positive")
    
    if distance < min_distance:
        raise ValueError(f"❌ Distance cannot be less than {min_distance} km")
    
    if distance > max_distance:
        raise ValueError(f"❌ Distance cannot exceed {max_distance} km")
    
    return distance


def validate_rating_score(value: int) -> int:
    """
    Reyting balli validate qilish (1-5).
    """
    if not isinstance(value, int) or value < 1 or value > 5:
        raise ValueError(f"❌ Rating must be between 1 and 5: {value}")
    
    return value


def validate_text_no_sql_injection(value: str, max_length: int = 1000) -> str:
    """
    SQL injection'dan himoya qilish.
    Xavfli SQL keywords'ni tekshirish.
    """
    if not isinstance(value, str):
        raise ValueError("❌ Must be string")
    
    if len(value) > max_length:
        raise ValueError(f"❌ Text too long (max {max_length} characters)")
    
    # Xavfli patterns
    dangerous_patterns = [
        r"(\bUNION\b|\bSELECT\b|\bDROP\b|\bINJECT\b|\bEXECUTE\b)",  # SQL keywords
        r"(--|;|\/\*|\*\/)",  # SQL comments
        r"(\$\{|__proto__|constructor)",  # Prototype pollution
    ]
    
    value_upper = value.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_upper):
            raise ValueError(f"❌ Invalid characters detected in text")
    
    return value.strip()


# ─────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS WITH VALIDATION
# ─────────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    """
    skip: int = Field(0, ge=0, description="Skip first N records")
    limit: int = Field(20, ge=1, le=100, description="Return max N records")
    
    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        """Limit ko'pi bo'lsa 100 bo'ladi."""
        return min(v, 100)


class CoordinatesSchema(BaseModel):
    """
    GPS coordinates schema.
    """
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (-180 to 180)")


class AddressSchema(BaseModel):
    """
    Manzil schema with GPS.
    """
    city: str = Field(..., min_length=2, max_length=100, description="Shahar nomi")
    region: Optional[str] = Field(None, max_length=100, description="Viloyat/Region")
    address: Optional[str] = Field(None, max_length=300, description="Ko'proq ma'lumot")
    landmark: Optional[str] = Field(None, max_length=200, description="Mo'ljal")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    @field_validator("city", "region", "address", "landmark")
    @classmethod
    def sanitize_text(cls, v):
        """Remove potentially harmful content."""
        if not v:
            return v
        return validate_text_no_sql_injection(v)


class PriceSchema(BaseModel):
    """
    Narx schema.
    """
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Narx summasi")
    currency: str = Field("UZS", min_length=3, max_length=3, description="Valyuta kodi (UZS, USD)")


class CreateOrderSchema(BaseModel):
    """
    Yangi order yaratish schema.
    """
    cargo_name: str = Field(..., min_length=3, max_length=200, description="Yuk nomi")
    cargo_description: Optional[str] = Field(None, max_length=500, description="Yuk tavsifi")
    weight: Decimal = Field(..., gt=0, max_digits=6, decimal_places=2, description="Og'irlik (tonna)")
    volume: Optional[Decimal] = Field(None, gt=0, max_digits=6, decimal_places=2, description="Hajmi (m³)")
    
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Narx")
    currency: str = Field("UZS", min_length=3, max_length=3)
    
    required_truck_type_id: int = Field(..., gt=0, description="Kerakli mashina turi ID")
    
    @field_validator("cargo_name", "cargo_description")
    @classmethod
    def sanitize_cargo_text(cls, v):
        """Remove harmful content from cargo fields."""
        if not v:
            return v
        return validate_text_no_sql_injection(v, max_length=500)


# ─────────────────────────────────────────────────────────────
# RATE LIMITING HELPER
# ─────────────────────────────────────────────────────────────

from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    """
    Simple in-memory rate limiter.
    Production da Redis ishlatish tavsiya qilinadi.
    """
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Identifier (user_id, IP address, etc.)
            max_requests: Max requests per window
            window_seconds: Time window in seconds
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add new request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()

