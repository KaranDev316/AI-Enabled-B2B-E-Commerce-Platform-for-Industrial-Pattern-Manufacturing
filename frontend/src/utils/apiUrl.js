// Authentication is only forwarded to the API served by this site's proxy.
export function isInternalApiUrl(input, origin = window.location.origin) {
  try {
    const url = new URL(typeof input === 'string' ? input : input.url, origin);
    return url.origin === origin && (url.pathname === '/api' || url.pathname.startsWith('/api/'));
  } catch {
    return false;
  }
}
