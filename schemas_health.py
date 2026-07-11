from pydantic import BaseModel, EmailStr
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    session_token: Optional[str] = None

class PlaceResult(BaseModel):
    place_id: str
    name: str
    address: str
    rating: float
    reviews: int
    thumbnail: str
    data_id: str

class ScanRequest(BaseModel):
    place_id: str
    name: str
    address: str
    category: str # Extracted from user input or Google places
    city: str # Extracted from address
    session_token: Optional[str] = None

class CompetitorData(BaseModel):
    name: str
    rating: float
    reviews: int

class ScanResponse(BaseModel):
    scan_id: int
    headline_score: int
    gmb_score: int
    seo_score: int
    geo_aeo_score: int
    business_rating: float
    business_reviews: int
    competitor_avg_reviews: int
    competitor_top_reviews: int
    competitors: List[CompetitorData]
    issues: List[str]

class CaptureLeadRequest(BaseModel):
    scan_id: int
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
