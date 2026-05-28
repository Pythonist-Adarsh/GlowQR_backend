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
                {"width": 300, "height": 300, "crop": "fill", "gravity": "auto"},
                {"quality": "auto", "fetch_format": "auto"}
            ]
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None
