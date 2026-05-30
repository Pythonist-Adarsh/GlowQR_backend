from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

# --- Auth ---
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
    trial_ends_at: Optional[datetime] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    user: User
    access_token: str
    refresh_token: str
    token_type: str
    onboarding_completed: bool = False

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    onboarding_completed: bool = False

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class AuthMeResponse(BaseModel):
    user: dict
    business: Optional[dict] = None

# --- Business ---
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
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    category: Optional[str] = None
    price_range: Optional[str] = None
    cuisine_speciality: Optional[str] = None
    dietary_options: Optional[List[str]] = None
    signature_dish: Optional[str] = None
    highlighted_dishes: Optional[str] = None
    excluded_dishes: Optional[str] = None
    welcome_message: Optional[str] = None
    ai_variant_count: Optional[int] = 3
    review_language: str = "english"
    negative_filter_enabled: bool = False
    animation_style: str = "glow_float"
    seasonal_theme: Optional[str] = None
    business_hours: Optional[Any] = None
    menu_data: Optional[Any] = None

class BusinessCreate(BusinessBase):
    pass

class Business(BusinessBase):
    id: int
    owner_id: int
    is_onboarded: bool
    onboarding_step: int
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True

# --- Onboarding ---
class OnboardingStep1(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    tagline: Optional[str] = None
    website: Optional[str] = None
    google_review_url: str
    place_id: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None

class OnboardingStep3(BaseModel):
    category: str
    price_range: Optional[str] = None
    cuisine_speciality: Optional[str] = None
    dietary_options: Optional[List[str]] = None

class OnboardingStep4(BaseModel):
    signature_dish: Optional[str] = None
    highlighted_dishes: Optional[str] = None
    excluded_dishes: Optional[str] = None
    menu_categories: Optional[List[Any]] = None

# Step 2 and Step 5 handle file uploads, so their schemas will be processed directly in the route via Form() and File()

# --- Scans & Reviews ---
class ScanRecordCreate(BaseModel):
    qr_slug: str
    session_id: Optional[str] = None
    stage: str
    device_type: Optional[str] = None
    overall_rating: Optional[int] = None
    food_rating: Optional[int] = None
    service_rating: Optional[int] = None
    atmosphere_rating: Optional[int] = None
    selected_items: Optional[List[str]] = None
    meal_type: Optional[str] = None
    price_range: Optional[str] = None
    seating_type: Optional[str] = None
    wait_time: Optional[str] = None
    review_variant: Optional[int] = None
    review_text: Optional[str] = None
    was_negative: Optional[bool] = None

class FeedbackSubmitCreate(BaseModel):
    qr_slug: str
    rating: int
    feedback: str
    session_id: Optional[str] = None

class ReviewGenerationRequest(BaseModel):
    qr_slug: str
    business_name: str
    tagline: Optional[str] = None
    category: str
    overall_rating: int
    food_rating: Optional[int] = None
    service_rating: Optional[int] = None
    atmosphere_rating: Optional[int] = None
    selected_items: List[str] = []
    meal_type: Optional[str] = None
    price_range: Optional[str] = None
    seating_type: Optional[str] = None
    wait_time: Optional[str] = None
    signature_dish: Optional[str] = None
    language: str = "english"
    variant_count: int = 3
    plan: str = "trial"
    city: Optional[str] = None

class MenuItemAnalytics(BaseModel):
    name: str
    count: int

class DailyAnalyticsResponse(BaseModel):
    date: str
    scans: int
    redirects: int
    avg_rating: Optional[float]
    top_items: List[MenuItemAnalytics]

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class QRCodeCreate(BaseModel):
    label: str

class QRCodeResponse(BaseModel):
    id: int
    slug: str
    label: str
    is_active: bool
    scan_url: str
    qr_image_url: Optional[str] = None
    created_at: datetime

# --- Upgrades ---
class UpgradeRequestCreate(BaseModel):
    plan: str
    contact_name: str
    phone: str
    amount: int
    utr_number: Optional[str] = None
    payment_method: str = "upi"

class AdminSettingsUpdate(BaseModel):
    upi_id: Optional[str] = None
    basic_plan_price: Optional[int] = None
    premium_plan_price: Optional[int] = None
    notification_email: Optional[str] = None
    notify_on_upgrade: Optional[bool] = None
    notify_on_negative: Optional[bool] = None

class AdminSettingsResponse(BaseModel):
    upi_id: Optional[str] = None
    upi_qr_url: Optional[str] = None
    basic_plan_price: int
    premium_plan_price: int
    notification_email: Optional[str] = None
    notify_on_upgrade: bool
    notify_on_negative: bool

class AdminUserPlanUpdate(BaseModel):
    plan: str
    expires_at: Optional[datetime] = None
    admin_note: Optional[str] = None

class SubscriptionCreate(BaseModel):
    plan: str
