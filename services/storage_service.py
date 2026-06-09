import cloudinary
import cloudinary.uploader
import os
from io import BytesIO
from dotenv import load_dotenv

load_dotenv(override=True)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def upload_logo_to_cloudinary(file_bytes: bytes, business_id: int) -> str:
    """Uploads a logo to Cloudinary and returns the secure URL."""
    try:
        response = cloudinary.uploader.upload(
            file_bytes,
            folder=f"glowqr/logos/{business_id}",
            transformation=[
                {"width": 500, "height": 500, "crop": "limit"},
                {"quality": "auto", "fetch_format": "auto"}
            ]
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None

async def upload_pdf_to_cloudinary(file_bytes: bytes, business_id: int, alert_id: str) -> str:
    """Uploads an evidence report PDF to Cloudinary and returns the secure URL."""
    try:
        response = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            folder=f"glowqr/evidence/{business_id}",
            public_id=f"report_{alert_id}",
            format="pdf"
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary PDF upload error: {e}")
        return None
