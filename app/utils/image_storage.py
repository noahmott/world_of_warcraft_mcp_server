"""
Image storage utility for uploading charts to Supabase Storage
"""

import os
import uuid
from typing import Optional
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseImageStorage:
    """Upload and serve generated chart images via Supabase Storage"""

    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured - image storage disabled")
            self.supabase: Optional[Client] = None
        else:
            self.supabase = create_client(supabase_url, supabase_key)
            self.bucket_name = "charts"  # Supabase storage bucket name

    async def upload_chart(self, image_bytes: bytes, filename: str = None, content_type: str = "image/png") -> Optional[str]:
        """
        Upload chart image to Supabase Storage and return public URL

        Args:
            image_bytes: Raw image bytes
            filename: Optional filename (generates UUID if not provided)
            content_type: MIME type of the image

        Returns:
            Public URL to access the image, or None if upload fails
        """
        if not self.supabase:
            logger.error("Supabase client not initialized")
            return None

        try:
            # Generate unique filename if not provided
            if not filename:
                filename = f"chart_{uuid.uuid4()}.png"

            # Upload to Supabase Storage
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=filename,
                file=image_bytes,
                file_options={"content-type": content_type}
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(filename)

            logger.info(f"Uploaded chart to Supabase: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Error uploading chart to Supabase: {str(e)}")
            return None

    async def upload_html(self, html_content: str, filename: str = None) -> Optional[str]:
        """
        Upload HTML content to Supabase Storage (deprecated - use PNG charts instead)

        Note: Supabase Storage blocks HTML files from rendering inline for security.
        This method is kept for compatibility but PNG charts should be used instead.

        Args:
            html_content: HTML string content
            filename: Optional filename (generates UUID if not provided)

        Returns:
            Public URL to access the HTML, or None if upload fails
        """
        if not self.supabase:
            logger.error("Supabase client not initialized")
            return None

        try:
            # Generate unique filename if not provided
            if not filename:
                filename = f"chart_{uuid.uuid4()}.html"

            # Convert string to bytes
            html_bytes = html_content.encode('utf-8')

            # Upload to Supabase Storage
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=filename,
                file=html_bytes,
                file_options={
                    "content-type": "text/html; charset=utf-8",
                    "cache-control": "public, max-age=3600"
                }
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(filename)

            logger.info(f"Uploaded HTML chart to Supabase: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Error uploading HTML to Supabase: {str(e)}")
            return None

    async def delete_chart(self, filename: str) -> bool:
        """
        Delete a chart from Supabase Storage

        Args:
            filename: Name of the file to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.supabase:
            return False

        try:
            self.supabase.storage.from_(self.bucket_name).remove([filename])
            logger.info(f"Deleted chart from Supabase: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chart from Supabase: {str(e)}")
            return False


# Global instance
image_storage = SupabaseImageStorage()
