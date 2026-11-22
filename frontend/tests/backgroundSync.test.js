import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { build } from 'esbuild-wasm';

test('background sync skips overlapping requests, recovers from rejection and cleans up polling', async () => {
  const effects = [], cleanups = [], listeners = new Map();
  let tick, cleared = false;
  const original = { window: globalThis.window, document: globalThis.document,
    setInterval: globalThis.setInterval, clearInterval: globalThis.clearInterval };
  globalThis.__refreshHookHarness = {
    useRef: current => ({ current }), useState: value => [value, () => {}],
    useCallback: fn => fn, useEffect: fn => effects.push(fn),
  };
  globalThis.window = {
    addEventListener: (name, fn) => listeners.set(name, fn),
    removeEventListener: name => listeners.delete(name),
  };
  globalThis.document = { ...window, visibilityState: 'visible' };
  globalThis.setInterval = fn => { tick = fn; return 1; };
  globalThis.clearInterval = () => { cleared = true; };
  try {
    const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
    const compiled = await build({
      entryPoints: [path.join(frontend, 'src/utils/kpcLiveSync.jsx')], bundle: true, platform: 'node', format: 'cjs', write: false,
      plugins: [{ name: 'controlled-react-hooks', setup(builder) {
        builder.onResolve({ filter: /^react$/ }, () => ({ path: 'react', namespace: 'test-hooks' }));
        builder.onLoad({ filter: /.*/, namespace: 'test-hooks' }, () => ({ contents:
          'export const { useRef, useState, useCallback, useEffect } = globalThis.__refreshHookHarness; export default {};' }));
      } }],
    });
    const module = { exports: {} };
    new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
    let calls = 0, finish;
    module.exports.useKpcLiveSync(() => {
      calls++;
      return new Promise(resolve => { finish = resolve; });
    }, 4000);
    effects.forEach(effect => { const cleanup = effect(); if (cleanup) cleanups.push(cleanup); });
    tick();
    tick();
    listeners.get('focus')();
    assert.equal(calls, 1, 'slow refreshes must not overlap');
    finish();
    await Promise.resolve();
    tick();
    assert.equal(calls, 2, 'polling resumes after completion');
    finish();
    await Promise.resolve();
    document.visibilityState = 'hidden';
    tick();
    assert.equal(calls, 2, 'hidden tabs do not poll');
    document.visibilityState = 'visible';
    // Exercise a hook instance whose async refresh rejects.
    const oldEffects = effects.length;
    module.exports.useKpcLiveSync(async () => { throw new Error('Offline'); }, 4000);
    effects.slice(oldEffects).forEach(effect => { const cleanup = effect(); if (cleanup) cleanups.push(cleanup); });
    // This event handler returns a promise only internally; it must handle rejection itself.
    const originalError = console.error;
    let logged = 0;
    console.error = () => { logged++; };
    try { tick(); await Promise.resolve(); tick(); await Promise.resolve(); }
    finally { console.error = originalError; }
    assert.equal(logged, 2, 'failed requests release the in-flight guard for the next retry');
  } finally {
    cleanups.forEach(cleanup => cleanup());
    assert.equal(cleared, true);
    assert.equal(listeners.size, 0);
    Object.assign(globalThis, original);
    delete globalThis.__refreshHookHarness;
  }
});
