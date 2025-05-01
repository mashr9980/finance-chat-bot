from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any

# User Schema for Signup & Login
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    profession_id: int  # Added profession_id for signup

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str  # Added role to token response
    is_new_user: Optional[bool] = False
    needs_profession: Optional[bool] = False

# Google Authentication Schema
class GoogleAuthRequest(BaseModel):
    id_token: str
    redirect_url: Optional[str] = None

class GoogleProfile(BaseModel):
    google_id: str
    email: EmailStr
    name: Optional[str] = None
    picture_url: Optional[str] = None

# Chat Schema
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    response: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProfessionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class ProfessionList(BaseModel):
    professions: List[ProfessionResponse]

# Payment Schema
class PaymentRequest(BaseModel):
    amount: int  
    currency: str = "usd"
    description: str
    email: str

class PaymentStatusResponse(BaseModel):
    status: str
    payment_date: Optional[str] = None
    expiry_date: Optional[str] = None
    payment_id: Optional[str] = None
    payment_amount: Optional[int] = None

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str

class PaymentSuccessResponse(BaseModel):
    message: str
    session_id: str

# Schema for User Profile
class UserProfile(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    status: str
    profession: Optional[ProfessionResponse] = None
    google_connected: bool = False
    profile_picture: Optional[str] = None
    payment_status: Optional[str] = "free"
    payment_expiry: Optional[str] = None

# Schema for setting user's profession after Google login
class SetProfession(BaseModel):
    profession_id: int

# Schema for Profession Prompts - simplified without questions JSON structure
class ProfessionWithPrompt(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str  # Single text field for the full prompt

class ProfessionPromptResponse(BaseModel):
    id: int
    profession_id: int
    profession_name: str
    system_prompt: str  # Single text field for the full prompt

class ProfessionPromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: str  # Single text field for the prompt

# Schema for Report Tracking
class ReportTrackingResponse(BaseModel):
    id: int
    user_id: int
    report_type: str
    created_at: str
    report_name: Optional[str] = None

# Schema for Report Generation
class ReportRequest(BaseModel):
    business_name: Optional[str] = None
    owner_name: Optional[str] = None