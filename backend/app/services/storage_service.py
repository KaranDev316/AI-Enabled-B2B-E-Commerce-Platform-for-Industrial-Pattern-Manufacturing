import logging
from pathlib import Path
from typing import Optional
import uuid

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.supabase_url = (self.settings.supabase_url or '').rstrip('/')
        self.supabase_key = self.settings.supabase_service_role_key or ''
        self.bucket = self.settings.supabase_storage_bucket or 'kpc-private-files'
        self.local_dir = self.settings.private_storage_dir

        if not self.is_supabase_configured():
            self.local_dir.mkdir(parents=True, exist_ok=True)

    def is_supabase_configured(self) -> bool:
        """Determines if remote private Supabase Storage is configured."""
        return bool(self.supabase_url and self.supabase_key)

    def generate_storage_key(self, rfq_id: int, original_filename: str) -> str:
        """Generates an unguessable private storage key scoped under an RFQ path."""
        ext = Path(original_filename).suffix.lower()
        unique_token = uuid.uuid4().hex
        return f"rfqs/{rfq_id}/{unique_token}{ext}"

    def generate_support_storage_key(self, ticket_id: int, original_filename: str) -> str:
        """Generates an unguessable private storage key scoped under a support ticket path."""
        ext = Path(original_filename).suffix.lower()
        unique_token = uuid.uuid4().hex
        return f"support/{ticket_id}/{unique_token}{ext}"

    def save_file(self, storage_key: str, content: bytes, content_type: str) -> None:
        """Stores file content in Supabase Storage or private local fallback."""
        if self.is_supabase_configured():
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_key}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
                "Content-Type": content_type,
                "x-upsert": "true",
            }
            try:
                response = httpx.post(url, headers=headers, content=content, timeout=30.0)
                if response.status_code not in (200, 201):
                    logger.error(f"Supabase upload failed: {response.status_code} {response.text}")
                    raise RuntimeError(f"Failed to store file in Supabase: {response.text}")
            except httpx.RequestError as exc:
                logger.error(f"Supabase network error: {exc}")
                raise RuntimeError(f"Storage backend unavailable: {exc}")
        else:
            # Safe local fallback inside .private_storage
            target_path = (self.local_dir / storage_key).resolve()
            if not str(target_path).startswith(str(self.local_dir.resolve())):
                raise ValueError("Invalid storage path traversal.")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)

    def get_file(self, storage_key: str) -> bytes:
        """Retrieves raw file bytes from Supabase Storage or private local fallback."""
        if self.is_supabase_configured():
            # First attempt authenticated signed/download endpoint
            url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket}/{storage_key}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
            }
            try:
                response = httpx.get(url, headers=headers, timeout=30.0)
                if response.status_code == 200:
                    return response.content
                # Fallback to standard object path with service key
                alt_url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_key}"
                alt_res = httpx.get(alt_url, headers=headers, timeout=30.0)
                if alt_res.status_code == 200:
                    return alt_res.content
                raise FileNotFoundError(f"File not found in storage: {storage_key}")
            except httpx.RequestError as exc:
                logger.error(f"Supabase download error: {exc}")
                raise RuntimeError(f"Storage backend unavailable: {exc}")
        else:
            target_path = (self.local_dir / storage_key).resolve()
            if not str(target_path).startswith(str(self.local_dir.resolve())):
                raise ValueError("Invalid storage path traversal.")
            if not target_path.is_file():
                raise FileNotFoundError(f"File not found: {storage_key}")
            return target_path.read_bytes()

    def delete_file(self, storage_key: str) -> None:
        """Deletes file from Supabase Storage or private local fallback."""
        if self.is_supabase_configured():
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_key}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
            }
            try:
                httpx.delete(url, headers=headers, timeout=10.0)
            except Exception as exc:
                logger.warning(f"Failed to delete file from Supabase: {exc}")
        else:
            target_path = (self.local_dir / storage_key).resolve()
            if str(target_path).startswith(str(self.local_dir.resolve())) and target_path.is_file():
                try:
                    target_path.unlink()
                except Exception as exc:
                    logger.warning(f"Failed to delete local file: {exc}")


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
