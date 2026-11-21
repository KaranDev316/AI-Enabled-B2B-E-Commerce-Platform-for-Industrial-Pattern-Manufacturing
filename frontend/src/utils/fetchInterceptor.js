/**
 * Global Fetch Interceptor for Tab-Isolated Auth & Anti-Caching.
 * 
 * Guarantees:
 * 1. Each browser tab sends its own Authorization: Bearer <sessionStorage_token>.
 * 2. All GET API requests include Cache-Control: no-store, no-cache to eliminate stale caches.
 * 3. All state-changing mutations (POST, PUT, PATCH, DELETE) automatically include X-CSRF-Token.
 */

if (typeof window !== 'undefined' && !window.__kpcFetchInterceptorInstalled) {
  window.__kpcFetchInterceptorInstalled = true;
  const originalFetch = window.fetch;

  window.fetch = async function (input, init = {}) {
    let url = typeof input === 'string' ? input : (input && input.url ? input.url : '');

    // Target internal API requests
    const isApiRequest = url.startsWith('/api') || url.includes('/api/');

    if (isApiRequest) {
      const token = sessionStorage.getItem('kpc_auth_token');
      const csrfToken = sessionStorage.getItem('kpc_csrf_token');

      // Extract existing headers cleanly
      const headers = new Headers(
        init.headers || (typeof input === 'object' && input.headers ? input.headers : {})
      );

      // 1. Prioritize tab-isolated Bearer token from sessionStorage
      if (token && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      // 2. Strict anti-caching for GET requests
      const method = (init.method || (typeof input === 'object' && input.method ? input.method : 'GET')).toUpperCase();
      if (method === 'GET') {
        if (!headers.has('Cache-Control')) {
          headers.set('Cache-Control', 'no-store, no-cache, must-revalidate');
        }
        if (!headers.has('Pragma')) {
          headers.set('Pragma', 'no-cache');
        }
      }

      // 3. Attach session CSRF token for mutations if not explicitly set
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && csrfToken && !headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', csrfToken);
      }

      init = {
        ...init,
        headers,
        credentials: init.credentials || 'same-origin',
      };
    }

    return originalFetch.call(this, input, init);
  };
}
