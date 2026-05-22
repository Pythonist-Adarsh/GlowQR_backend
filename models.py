from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # Nullable for OAuth users
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Subscription / Billing
    plan = Column(String, default="trial")
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    razorpay_customer_id = Column(String, nullable=True)
    razorpay_subscription_id = Column(String, nullable=True)

    businesses = relationship("Business", back_populates="owner")

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    tagline = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, default="#6366F1")
    google_review_url = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # Contact & Identity
    phone_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    owner_email = Column(String, nullable=True)
    
    # Location
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    area_locality = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    
    # Google Integration
    place_id = Column(String, nullable=True)
    google_rating = Column(String, nullable=True)
    review_count = Column(String, nullable=True)
    
    # Business Details
    category = Column(String, nullable=True)
    price_range = Column(String, nullable=True)
    cuisine_speciality = Column(String, nullable=True)
    dietary_options = Column(JSON, nullable=True)
    
    # Menu Highlights
    signature_dish = Column(String, nullable=True)
    highlighted_dishes = Column(String, nullable=True)
    excluded_dishes = Column(String, nullable=True)
    
    # Experience Settings
    experience_type = Column(String, default="classic")
    welcome_message = Column(String, nullable=True)
    ai_variant_count = Column(String, nullable=True)
    review_language = Column(String, default="English")
    negative_filter_enabled = Column(Boolean, default=False)
    animation_style = Column(String, default="Glow & Float")
    seasonal_theme = Column(String, nullable=True)
    
    # Structured Data
    business_hours = Column(JSON, nullable=True)
    menu_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="businesses")
    scans = relationship("ScanEvent", back_populates="business")
    feedback = relationship("NegativeFeedback", back_populates="business")

class ScanEvent(Base):
    __tablename__ = "scan_events"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    device_type = Column(String, nullable=True)
    
    business = relationship("Business", back_populates="scans")

class NegativeFeedback(Base):
    __tablename__ = "negative_feedback"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    rating = Column(Integer)
    feedback_text = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="feedback")
