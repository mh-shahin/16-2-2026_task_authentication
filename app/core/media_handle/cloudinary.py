import cloudinary
import cloudinary.uploader
from app.core.config import settings
from typing import Optional

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


def upload_image(file_bytes: bytes, folder: str = "events") -> Optional[dict]:
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            resource_type="image"
        )
        return {
            'url': result.get('secure_url'),
            'public_id': result.get('public_id')
        }
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None


def delete_image(public_id: str) -> bool:
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
        return False