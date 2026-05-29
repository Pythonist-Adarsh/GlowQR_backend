from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float, text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # Nullable for OAuth users
    full_name = Column(String)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Subscription / Billing
    plan = Column(String, default="trial")
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    razorpay_customer_id = Column(String, nullable=True)
    
    # Notifications & Preferences
    notif_new_review = Column(Boolean, default=True)
    notif_negative_alert = Column(Boolean, default=True)
    whatsapp_alerts = Column(Boolean, default=False)
    whatsapp_number = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    businesses = relationship("Business", back_populates="owner")
    upgrade_requests = relationship("UpgradeRequest", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    category = Column(String, nullable=True)
    
    # Contact
    phone_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    owner_email = Column(String, nullable=True)
    
    # Location
    address = Column(String, nullable=True)
    area_locality = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    
    # Google Integration
    place_id = Column(String, nullable=True)
    google_review_url = Column(String, nullable=True)
    google_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    
    # Branding
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, default="#6366F1")
    tagline = Column(String, nullable=True)
    welcome_message = Column(String, nullable=True)
    
    # Menu & Details
    menu_data = Column(JSON, nullable=True)
    price_range = Column(String, nullable=True)
    cuisine_speciality = Column(String, nullable=True)
    dietary_options = Column(JSON, nullable=True)
    signature_dish = Column(String, nullable=True)
    highlighted_dishes = Column(String, nullable=True)
    excluded_dishes = Column(String, nullable=True)
    business_hours = Column(JSON, nullable=True)
    
    # Experience Settings
    animation_style = Column(String, default="glow_float")
    particle_intensity = Column(Integer, default=5)
    seasonal_theme = Column(String, nullable=True)
    review_language = Column(String, default="english")
    ai_variant_count = Column(Integer, default=3)
    negative_filter_enabled = Column(Boolean, default=False)
    
    # Onboarding State
    onboarding_step = Column(Integer, default=0)
    is_onboarded = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="businesses")
    menu_items = relationship("MenuItem", back_populates="business")
    qr_codes = relationship("QRCode", back_populates="business")
    scans = relationship("ScanEvent", back_populates="business")
    feedback = relationship("NegativeFeedback", back_populates="business")

class MenuItem(Base):
    __tablename__ = "menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    name = Column(String)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    business = relationship("Business", back_populates="menu_items")

class QRCode(Base):
    __tablename__ = "qr_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    label = Column(String)
    slug = Column(String, unique=True, index=True)
    qr_image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    business = relationship("Business", back_populates="qr_codes")
    scans = relationship("ScanEvent", back_populates="qr_code")

class ScanEvent(Base):
    __tablename__ = "scan_events"

    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id", ondelete="CASCADE"), nullable=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    session_id = Column(String, unique=True, index=True, nullable=True)
    stage = Column(String, default="scanned")
    
    # Analytics / Tracking additions
    qr_slug = Column(String, index=True, nullable=True)
    step_logs = Column(JSON, default=dict) # Tracks timestamps of each step
    redirected_to_google = Column(Boolean, default=False)
    time_spent_seconds = Column(Integer, nullable=True)
    
    overall_rating = Column(Integer, nullable=True)
    food_rating = Column(Integer, nullable=True)
    service_rating = Column(Integer, nullable=True)
    atmosphere_rating = Column(Integer, nullable=True)
    
    selected_items = Column(ARRAY(String), nullable=True)
    meal_type = Column(String, nullable=True)
    price_range = Column(String, nullable=True)
    seating_type = Column(String, nullable=True)
    wait_time = Column(String, nullable=True)
    review_variant = Column(Integer, nullable=True)
    review_text = Column(String, nullable=True)
    was_negative = Column(Boolean, default=False)
    
    device_type = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_hash = Column(String, nullable=True)
    
    # Extracted by generated columns ideally, or manually populated via db triggers / python logic
    hour_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    business = relationship("Business", back_populates="scans")
    qr_code = relationship("QRCode", back_populates="scans")
    feedback = relationship("NegativeFeedback", back_populates="scan_event")

class NegativeFeedback(Base):
    __tablename__ = "negative_feedback"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    scan_event_id = Column(Integer, ForeignKey("scan_events.id", ondelete="CASCADE"), nullable=True)
    rating = Column(Integer)
    feedback_text = Column(String)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="feedback")
    scan_event = relationship("ScanEvent", back_populates="feedback")

class UpgradeRequest(Base):
    __tablename__ = "upgrade_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    business_name = Column(String)
    contact_name = Column(String)
    phone = Column(String)
    email = Column(String)
    plan_requested = Column(String)
    amount_paid = Column(Integer) # in paise usually, or whole rupees
    utr_number = Column(String, nullable=True)
    payment_method = Column(String)
    status = Column(String, default="pending") # pending/verified/rejected
    admin_note = Column(String, nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="upgrade_requests")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    plan = Column(String)
    status = Column(String) # active, completed, cancelled
    razorpay_subscription_id = Column(String, nullable=True)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    amount_paise = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="subscriptions")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="refresh_tokens")

class DailyAnalytics(Base):
    __tablename__ = "daily_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    date = Column(DateTime(timezone=True), index=True)
    
    total_scans = Column(Integer, default=0)
    google_redirects = Column(Integer, default=0)
    drop_off_step = Column(String, nullable=True)
    top_dishes = Column(JSON, nullable=True)
    avg_rating_given = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    business = relationship("Business")

class OnboardingRecord(Base):
    __tablename__ = "onboarding_records"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"))
    setup_payload = Column(JSON)
    plan_selected_at_onboarding = Column(String, nullable=True)
    
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    business = relationship("Business")
