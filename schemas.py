from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    is_active: bool
    plan: str
    trial_ends_at: Optional[Any] = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    user: User
    access_token: str
    token_type: str
    onboarding_completed: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str
    onboarding_completed: bool = False

class TokenData(BaseModel):
    email: Optional[str] = None

class BusinessBase(BaseModel):
    name: str
    slug: Optional[str] = None
    tagline: Optional[str] = None
    primary_color: str = "#6366F1"
    google_review_url: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    area_locality: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    owner_email: Optional[str] = None
    place_id: Optional[str] = None
    google_rating: Optional[str] = None
    review_count: Optional[str] = None
    category: Optional[str] = None
    price_range: Optional[str] = None
    cuisine_speciality: Optional[str] = None
    dietary_options: Optional[List[str]] = None
    signature_dish: Optional[str] = None
    highlighted_dishes: Optional[str] = None
    excluded_dishes: Optional[str] = None
    experience_type: str = "classic"
    welcome_message: Optional[str] = None
    ai_variant_count: Optional[str] = None
    review_language: str = "English"
    negative_filter_enabled: bool = False
    animation_style: str = "Glow & Float"
    seasonal_theme: Optional[str] = None
    business_hours: Optional[Any] = None
    menu_data: Optional[Any] = None

class BusinessCreate(BusinessBase):
    pass

class Business(BusinessBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True

class ScanRecordCreate(BaseModel):
    business_id: int
    device_type: Optional[str] = None

class FeedbackSubmitCreate(BaseModel):
    business_id: int
    rating: int
    feedback_text: str

class ReviewGenerationRequest(BaseModel):
    business_id: int
    rating: int
    selections: Any # selected chips, meal type, etc.

class SubscriptionCreate(BaseModel):
    plan: str # 'basic' or 'premium'

class MenuExtractRequest(BaseModel):
    image_base64: str
