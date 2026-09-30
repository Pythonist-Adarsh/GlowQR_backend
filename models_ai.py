from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.sql import func
from database import Base

class BusinessAIProfile(Base):
    __tablename__ = "business_ai_profiles"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    slug = Column(String, unique=True, index=True)
    faq_json = Column(JSON, default=list)
    summary_text = Column(Text, nullable=True)
    structured_facts_json = Column(JSON, default=dict)
    last_generated_at = Column(DateTime(timezone=True), server_default=func.now())
    is_published = Column(Boolean, default=False)

class AIVisibilityLog(Base):
    __tablename__ = "ai_visibility_log"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    month = Column(String, index=True) # e.g., '2026-06'
    engine = Column(String) # 'chatgpt', 'gemini', 'claude', 'perplexity'
    mentioned = Column(Boolean, default=False)
    response_snippet = Column(Text, nullable=True)
    competitor_mentioned = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
