from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Literal, Optional
import re


class ProfileModel(BaseModel):
    """User health profile for analysis."""
    age: int = Field(..., ge=18, le=100)
    gender: Literal["male", "female"]
    smoking_status: Literal["smoker", "non-smoker"]
    activity_level: Literal["sedentary", "moderate", "active"]


class UserRegisterModel(BaseModel):
    """User registration request model."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        v = v.lower().strip()
        # Simple email regex validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLoginModel(BaseModel):
    """User login request model."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class TokenResponseModel(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponseModel(BaseModel):
    """User data response model (safe, no password)."""
    id: str
    email: str
    created_at: str


class ErrorResponseModel(BaseModel):
    """Standard error response model."""
    status: str = "error"
    message: str
    code: Optional[str] = None
    errors: Optional[list] = None

