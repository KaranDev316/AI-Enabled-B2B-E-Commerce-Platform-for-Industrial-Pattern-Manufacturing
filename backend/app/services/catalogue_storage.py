"""Private catalogue storage with safe, actionable upload failures."""
import httpx
from urllib.parse import quote, urlparse
from app.services.storage_service import StorageService


class CatalogueStorageError(RuntimeError):
    """A safe user-facing error; never contains credentials or remote response text."""


class CatalogueStorage(StorageService):
    def save_file(self, storage_key: str, content: bytes, content_type: str) -> None:
        parsed = urlparse(self.supabase_url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path not in ('', '/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise CatalogueStorageError('Set SUPABASE_URL to your HTTPS project URL only, without a dashboard or storage path. Restart the backend afterward.')
        if not self.supabase_key or self.supabase_key == 'YOUR_PRIVATE_SERVER_SIDE_KEY':
            raise CatalogueStorageError('Set the actual server-side Supabase service-role key in backend .env and restart the backend.')
        url = f'{self.supabase_url}/storage/v1/object/{quote(self.bucket, safe="")}/{quote(storage_key, safe="/")}'
        try:
            response = httpx.post(url, headers={
                'Authorization': f'Bearer {self.supabase_key}', 'apikey': self.supabase_key,
                'Content-Type': content_type, 'x-upsert': 'false'}, content=content, timeout=30.0)
        except httpx.TimeoutException:
            raise CatalogueStorageError('Supabase upload timed out. Check your connection and project availability, then retry.') from None
        except httpx.RequestError:
            raise CatalogueStorageError('Cannot reach Supabase Storage. Check SUPABASE_URL, internet access and project availability.') from None
        if response.status_code in (200, 201):
            return
        # Classify remote errors without ever reflecting remote text or credentials.
        try:
            body = response.json()
            hint = ' '.join(str(body.get(k, '')) for k in ('error', 'message', 'code')).lower() if isinstance(body, dict) else ''
        except ValueError:
            hint = ''
        if 'bucket' in hint and ('not found' in hint or 'not exist' in hint):
            reason = 'The configured Storage bucket does not exist in this Supabase project. Create it as a private bucket or correct SUPABASE_STORAGE_BUCKET.'
        elif response.status_code == 401 or any(term in hint for term in ('invalid jwt', 'invalid api key', 'expired jwt', 'invalid signature')):
            reason = 'Supabase rejected the backend key. Use the service-role key from the same project as SUPABASE_URL, then restart the backend.'
        elif response.status_code == 403 or any(term in hint for term in ('row-level security', 'unauthorized', 'access denied')):
            reason = 'Supabase denied upload access. Use the project service-role key in backend .env, not the anon/publishable key. Keep the bucket private.'
        elif response.status_code == 413 or 'maximum allowed size' in hint:
            reason = 'The Storage bucket file-size limit is too small. Allow images up to 20 MB in its settings.'
        elif 'mime' in hint or 'content type' in hint:
            reason = 'The Storage bucket rejects this image type. Allow image/jpeg and image/png in its settings.'
        elif response.status_code == 404:
            reason = 'Supabase Storage was not found. Check your project URL, bucket name and whether the project is paused.'
        else:
            reason = f'Supabase rejected the upload (HTTP {response.status_code}). Check project availability and bucket settings.'
        raise CatalogueStorageError(reason)

    def delete_file(self, storage_key: str) -> None:
        if not self.is_supabase_configured():
            return super().delete_file(storage_key)
        response = httpx.delete(
            f'{self.supabase_url}/storage/v1/object/{quote(self.bucket, safe="")}/{quote(storage_key, safe="/")}',
            headers={'Authorization': f'Bearer {self.supabase_key}', 'apikey': self.supabase_key}, timeout=15.0)
        if response.status_code not in (200, 204, 404):
            raise RuntimeError('Catalogue storage cleanup failed.')


def get_catalogue_storage() -> StorageService:
    return CatalogueStorage()
