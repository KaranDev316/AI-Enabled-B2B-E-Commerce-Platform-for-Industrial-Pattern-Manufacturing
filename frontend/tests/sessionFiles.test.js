import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isInternalApiUrl } from '../src/utils/apiUrl.js';
import { fetchProtectedFile } from '../src/utils/protectedFiles.js';

test('only the same-origin API receives automatic credentials', async () => {
  const origin = 'https://kpc.example';
  for (const url of ['/api/auth/me', `${origin}/api/orders`]) assert.equal(isInternalApiUrl(url, origin), true);
  for (const url of ['https://outside.example/api/check', '//outside.example/api/check', '/api-other', '/page?next=/api/orders']) {
    assert.equal(isInternalApiUrl(url, origin), false, url);
  }
  const calls = [];
  globalThis.window = { location: { origin }, fetch: async (url, init) => { calls.push({ url, init }); } };
  globalThis.sessionStorage = { getItem: key => key === 'kpc_auth_token' ? 'tab-token' : 'tab-csrf' };
  await import('../src/utils/fetchInterceptor.js');
  await window.fetch('/api/orders', { method: 'POST' });
  assert.equal(calls[0].init.headers.get('Authorization'), 'Bearer tab-token');
  assert.equal(calls[0].init.headers.get('X-CSRF-Token'), 'tab-csrf');
  await window.fetch('https://outside.example/api/check', { method: 'POST' });
  assert.equal(calls[1].init.headers, undefined);
});

test('protected files use the tab token without cookies and reject missing sessions and errors', async () => {
  globalThis.window = { location: { origin: 'https://kpc.example' } };
  let token = 'customer-tab-token';
  globalThis.sessionStorage = { getItem: () => token };
  let calls = 0;
  globalThis.fetch = async (url, options) => {
    calls++;
    assert.equal(options.headers.Authorization, `Bearer ${token}`);
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    return new Response('demo invoice', { headers: { 'Content-Disposition': 'attachment; filename="invoice.html"' } });
  };
  const file = await fetchProtectedFile('/api/invoices/1/download');
  assert.equal(file.filename, 'invoice.html');
  assert.equal(await file.blob.text(), 'demo invoice');
  token = 'admin-tab-token';
  await fetchProtectedFile('/api/rfqs/1/files/1?disposition=inline');
  token = null;
  await assert.rejects(fetchProtectedFile('/api/invoices/1/download'), /sign in again/);
  assert.equal(calls, 2);
  await assert.rejects(fetchProtectedFile('https://outside.example/api/file'), /not supported/);
  token = 'expired';
  globalThis.fetch = async () => new Response('', { status: 401 });
  await assert.rejects(fetchProtectedFile('/api/invoices/1/download'), /expired/);
  globalThis.fetch = async () => new Response('', { status: 403 });
  await assert.rejects(fetchProtectedFile('/api/invoices/1/download'), /unavailable for your account/);
  globalThis.fetch = async () => new Response('', { status: 503 });
  await assert.rejects(fetchProtectedFile('/api/invoices/1/download'), /try again/);
});
