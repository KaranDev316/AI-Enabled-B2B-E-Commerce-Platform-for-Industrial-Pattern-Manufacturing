import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { build } from 'esbuild-wasm';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const compiled = await build({
  entryPoints: [path.join(frontend, 'src/components/QuotationWorkspace.jsx')],
  bundle: true, platform: 'node', format: 'cjs', write: false,
  loader: { '.css': 'empty' }, define: { 'import.meta.env': '{"VITE_API_BASE_URL":"/api"}' },
  plugins: [{ name: 'quotation-hooks', setup(builder) {
    builder.onResolve({ filter: /^react$/ }, () => ({ path: 'react', namespace: 'hooks' }));
    builder.onLoad({ filter: /.*/, namespace: 'hooks' }, () => ({ contents:
      'export const {useState,useEffect,useRef,createElement} = globalThis.__quotationHooks; export default {createElement};' }));
    builder.onResolve({ filter: /kpcLiveSync|ProtectedFiles/ }, () => ({ path: 'dependencies', namespace: 'stubs' }));
    builder.onLoad({ filter: /.*/, namespace: 'stubs' }, () => ({ contents:
      'export const emitKpcSync = () => {}; export const ProtectedDownload = "download";' }));
  } }],
});

function text(node) {
  if (Array.isArray(node)) return node.map(text).join('');
  if (node == null || typeof node === 'boolean') return '';
  return typeof node === 'object' ? text(node.props.children) : String(node);
}
function nodes(node, predicate) {
  if (Array.isArray(node)) return node.flatMap(child => nodes(child, predicate));
  if (!node || typeof node !== 'object') return [];
  return [...(predicate(node) ? [node] : []), ...nodes(node.props.children, predicate)];
}
const quote = {
  id: 7, version: 1, revision: 1, status: 'draft', is_latest: true,
  total: '118.00', subtotal: '100.00', tax_percent: '18', tax_amount: '18.00',
  tax_label: 'Sample tax (academic demonstration)', lead_time_days: 10, notes: '',
  created_at: '2026-11-24T00:00:00Z', decisions: [],
  items: [{ description: 'Tooling', quantity: 1, unit_price: '100.00', amount: '100.00' }],
};

async function harness(run, admin = true, initialResponse = { status: 200, body: [quote] }) {
  const original = { fetch: globalThis.fetch, window: globalThis.window };
  const state = [], effects = [], calls = [];
  let cursor = 0, tree, handler = async () => initialResponse;
  globalThis.__quotationHooks = {
    useState(initial) {
      const index = cursor++;
      if (!(index in state)) state[index] = initial;
      return [state[index], next => { state[index] = typeof next === 'function' ? next(state[index]) : next; }];
    },
    useRef: () => ({ current: null }), useEffect: fn => effects.push(fn),
    createElement: (type, props, ...children) => ({ type, props: { ...props, children } }),
  };
  globalThis.window = { confirm: () => true };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options });
    const { status, body } = await handler(url, options);
    return { ok: status < 400, status, json: async () => body };
  };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  function render() {
    cursor = 0;
    tree = module.exports.QuotationWorkspace({ admin, csrfToken: 'test', rfq: { id: 3, rfq_number: 'RFQ-TEST', title: 'Tooling', quantity: 1 } });
    return tree;
  }
  const api = {
    render, calls, text: () => text(render()), respond: fn => { handler = fn; },
    button: label => nodes(render(), n => n.type === 'button' && text(n) === label)[0],
    field: label => nodes(render(), n => n.props['aria-label'] === label)[0],
    save: async () => {
      nodes(render(), n => n.type === 'form' && n.props.id === 'quotation-draft')[0].props.onSubmit({ preventDefault() {} });
      await new Promise(resolve => setImmediate(resolve));
    },
  };
  try {
    render(); await effects[0](); await new Promise(resolve => setImmediate(resolve));
    await run(api);
  } finally {
    Object.assign(globalThis, original); delete globalThis.__quotationHooks;
  }
}

test('stale save preserves edits; discard requires confirmation and a successful reload', async () => {
  await harness(async h => {
    h.field('Item 1 description').props.onChange({ target: { value: 'My unsaved work' } });
    h.respond(async () => ({ status: 409, body: { detail: 'Quotation changed. Reload the latest version.' } }));
    await h.save();
    assert.match(h.text(), /Quotation changed/);
    assert.equal(h.field('Item 1 description').props.value, 'My unsaved work');
    let prompted = 0;
    window.confirm = () => { prompted++; return false; };
    const before = h.calls.length;
    h.button('Discard edits & reload').props.onClick();
    assert.equal(prompted, 1); assert.equal(h.calls.length, before);
    window.confirm = () => true;
    h.respond(async () => ({ status: 503, body: { detail: 'Temporarily unavailable' } }));
    h.button('Discard edits & reload').props.onClick();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(h.field('Item 1 description').props.value, 'My unsaved work');
    h.respond(async () => ({ status: 200, body: [{ ...quote, revision: 2, items: [{ ...quote.items[0], description: 'Other admin saved' }] }] }));
    h.button('Discard edits & reload').props.onClick();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(h.field('Item 1 description').props.value, 'Other admin saved');
    assert.equal(nodes(h.render(), n => n.type === 'select')[0].props.disabled, false);
  });
});

test('confirmed save followed by failed reload retains the new revision and reports saved state honestly', async () => {
  await harness(async h => {
    h.field('Item 1 description').props.onChange({ target: { value: 'Saved work' } });
    h.respond(async (_url, options) => options.method === 'PUT'
      ? { status: 200, body: { ...quote, revision: 2, items: [{ ...quote.items[0], description: 'Saved work' }] } }
      : { status: 503, body: { detail: 'Offline' } });
    await h.save();
    assert.match(h.text(), /Your change was saved, but the latest quotation could not be loaded/);
    assert.equal(h.field('Item 1 description').props.value, 'Saved work');
    await h.save();
    const writes = h.calls.filter(call => call.method === 'PUT');
    assert.equal(JSON.parse(writes[1].body).expected_revision, 2);
  });
});

test('initial retrieval failure does not claim the quotation list is empty', async () => {
  await harness(async h => {
    assert.match(h.text(), /Quotation service unavailable/);
    assert.doesNotMatch(h.text(), /No quotation yet/);
    assert.equal(h.button('Create blank quotation'), undefined);
    h.respond(async () => ({ status: 200, body: [] }));
    h.button('Reload').props.onClick();
    await new Promise(resolve => setImmediate(resolve));
    assert.match(h.text(), /No quotation yet/);
    assert.equal(h.button('Create blank quotation').props.disabled, false);
  }, true, { status: 503, body: { detail: 'Quotation service unavailable' } });
});

test('Admin and Customer summaries explicitly disclose sample academic tax', async () => {
  for (const admin of [true, false]) await harness(async h => {
    assert.match(h.text(), /Sample tax \(academic demonstration\)/);
    assert.match(h.text(), /Manual pricing · INR · Includes the sample tax shown below \(academic demonstration\)/);
    assert.match(h.text(), /118\.00/);
    if (admin) assert.match(h.text(), /Sample tax \(%\)/);
  }, admin);
});
