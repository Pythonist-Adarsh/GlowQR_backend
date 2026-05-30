from pydantic import BaseModel
from typing import Optional, Dict

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class AdminUserPlanUpdate(BaseModel):
    plan: str
    expires_at: Optional[str] = None

class AdminSettingsResponse(BaseModel):
    upi_id: Optional[str]
    upi_qr_url: Optional[str]
    basic_plan_price: int
    premium_plan_price: int
    notification_email: Optional[str]
    notify_on_upgrade: bool
    notify_on_negative: bool

    class Config:
        from_attributes = True

class AdminSettingsUpdate(BaseModel):
    upi_id: Optional[str] = None
    upi_qr_url: Optional[str] = None
    basic_plan_price: Optional[int] = None
    premium_plan_price: Optional[int] = None
    notification_email: Optional[str] = None
    notify_on_upgrade: Optional[bool] = None
    notify_on_negative: Optional[bool] = None
