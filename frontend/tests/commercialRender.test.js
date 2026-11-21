import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { build } from 'esbuild-wasm';

test('commercial screens render without hook initialization errors; demo controls preserve pending retries', async () => {
  const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const compiled = await build({
    stdin: { contents: `
      import React from 'react';
      import { renderToStaticMarkup } from 'react-dom/server';
      import { AuthProvider } from './src/context/AuthContext';
      import CustomerInvoices from './src/components/commercial/CustomerInvoicesPanel';
      import AdminInvoices from './src/components/commercial/AdminInvoicesPanel';
      import CustomerOrders from './src/components/commercial/CustomerOrdersPanel';
      import AdminOrders from './src/components/commercial/AdminOrdersPanel';
      import DemoPaymentForm from './src/components/commercial/DemoPaymentForm';
      export function screens() {
        return [CustomerInvoices, AdminInvoices, CustomerOrders, AdminOrders].map(Component => renderToStaticMarkup(<AuthProvider><Component /></AuthProvider>));
      }
      export function form(invoice) {
        return renderToStaticMarkup(<AuthProvider><DemoPaymentForm invoice={invoice} onRecorded={() => {}} /></AuthProvider>);
      }
    `, resolveDir: frontend, loader: 'jsx' },
    bundle: true, platform: 'node', format: 'cjs', write: false,
    loader: { '.css': 'empty', '.js': 'jsx' }, define: { 'import.meta.env': '{"VITE_API_BASE_URL":"/api"}' },
  });
  const saved = new Map([['kpc_auth_user', JSON.stringify({ id: 1, role: 'customer' })]]);
  globalThis.sessionStorage = { getItem: key => saved.get(key) || null };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  assert.equal(module.exports.screens().length, 4);
  const invoice = { id: 5, order_id: 1, status: 'partially_paid', outstanding_balance: '25.57' };
  const html = module.exports.form(invoice);
  assert.match(html, /Confirm Payment/);
  assert.match(html, /Amount \(INR\)/);
  assert.doesNotMatch(html, /UPI ID|Card Number|Bank Account/);
  saved.set('kpc_demo_payment:1:5', JSON.stringify({ idempotency_key: 'saved-key', amount: '25.57', outcome: 'succeeded' }));
  const retry = module.exports.form({ ...invoice, status: 'paid', outstanding_balance: '0.00' });
  assert.match(retry, /Retry Payment/);
  assert.match(retry, /disabled/);
});
