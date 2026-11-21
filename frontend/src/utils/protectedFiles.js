import { isInternalApiUrl } from './apiUrl.js';

export async function fetchProtectedFile(url, { signal } = {}) {
  if (!isInternalApiUrl(url)) throw new Error('This file address is not supported.');
  const token = sessionStorage.getItem('kpc_auth_token');
  if (!token) throw new Error('Please sign in again to access this file.');
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'omit',
    cache: 'no-store',
    redirect: 'error',
    signal,
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error('Your session has expired. Please sign in again.');
    if (response.status === 403 || response.status === 404) throw new Error('This file is unavailable for your account.');
    throw new Error('Unable to load the file. Please try again.');
  }
  const disposition = response.headers.get('Content-Disposition') || '';
  const filename = disposition.match(/filename="([^"]+)"/i)?.[1] || 'download';
  return { blob: await response.blob(), filename };
}
