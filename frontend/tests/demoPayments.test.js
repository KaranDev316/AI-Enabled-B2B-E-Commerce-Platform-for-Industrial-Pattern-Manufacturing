import assert from 'node:assert/strict';
import { test } from 'node:test';
import { paymentStorageKey, preparePayment, readPendingPayment, sendPaymentAttempt } from '../src/utils/demoPayments.js';

test('lost response and reload retain the original key and exact payment details', async () => {
  const saved = new Map();
  globalThis.sessionStorage = {
    getItem: key => saved.get(key) || null,
    setItem: (key, value) => saved.set(key, value),
  };
  const key = paymentStorageKey(1, 2);
  const attempt = preparePayment(key, '12.34', 'succeeded');
  assert.deepEqual(readPendingPayment(key), attempt);
  globalThis.fetch = async () => { throw new Error('Connection lost after submit'); };
  await assert.rejects(sendPaymentAttempt(2, attempt), /Connection lost/);
  assert.deepEqual(preparePayment(key, '99.00', 'failed'), attempt);
  let sent;
  globalThis.fetch = async (_, options) => {
    sent = JSON.parse(options.body);
    return Response.json({ id: 7, outcome: 'succeeded' });
  };
  assert.equal((await sendPaymentAttempt(2, readPendingPayment(key))).id, 7);
  assert.deepEqual(sent, attempt);
  assert.equal(readPendingPayment(paymentStorageKey(3, 2)), null);
});

test('definitive rejection is distinguished from uncertain server responses', async () => {
  for (const status of [400, 409, 422]) {
    globalThis.fetch = async () => Response.json({ detail: { message: 'Rejected' } }, { status });
    await assert.rejects(sendPaymentAttempt(2, {}), error => error.definitive === true);
  }
  for (const status of [401, 403, 404, 408, 429, 500, 503]) {
    globalThis.fetch = async () => new Response('', { status });
    await assert.rejects(sendPaymentAttempt(2, {}), error => error.definitive === false);
  }
  globalThis.fetch = async () => new Response('not JSON', { status: 200 });
  await assert.rejects(sendPaymentAttempt(2, {}), /could not be confirmed/);
});
