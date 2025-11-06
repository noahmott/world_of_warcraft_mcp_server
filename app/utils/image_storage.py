"""
Image storage utility for serving generated charts via URLs
"""

import os
import uuid
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ImageStorage:
    """Store and serve generated chart images via URLs"""

    def __init__(self):
        # Use a temporary directory for storing images
        self.storage_dir = Path("/tmp/chart_images")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Get base URL from environment or use default
        self.base_url = os.getenv("APP_BASE_URL", "https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com")

    def save_image(self, image_bytes: bytes, extension: str = "png") -> str:
        """
        Save image bytes to storage and return URL

        Args:
            image_bytes: Raw image bytes
            extension: File extension (png, jpg, etc.)

        Returns:
            Public URL to access the image
        """
        try:
            # Generate unique filename
            filename = f"{uuid.uuid4()}.{extension}"
            filepath = self.storage_dir / filename

            # Save image
            with open(filepath, 'wb') as f:
                f.write(image_bytes)

            # Return URL
            url = f"{self.base_url}/static/charts/{filename}"
            logger.info(f"Saved chart image: {url}")
            return url

        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            raise

    def cleanup_old_images(self, max_age_hours: int = 24):
        """
        Clean up old chart images

        Args:
            max_age_hours: Delete images older than this many hours
        """
        import time

        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for filepath in self.storage_dir.glob("*.png"):
                file_age = current_time - filepath.stat().st_mtime
                if file_age > max_age_seconds:
                    filepath.unlink()
                    logger.info(f"Deleted old chart image: {filepath.name}")

        except Exception as e:
            logger.error(f"Error cleaning up images: {str(e)}")


# Global instance
image_storage = ImageStorage()
