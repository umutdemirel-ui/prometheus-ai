import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';

const port = 43000 + Math.floor(Math.random() * 1000);
const origin = `http://127.0.0.1:${port}`;
let child;
before(async () => {
  child = spawn(process.execPath, ['server.mjs'], { env: { ...process.env, PORT: String(port), AI_PROVIDER: 'ollama', AI_MODEL: 'test-model' }, stdio: 'ignore' });
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    try { if ((await fetch(`${origin}/api/status`)).ok) return; } catch {}
    await new Promise(r => setTimeout(r, 60));
  }
  throw new Error('Test server did not start');
});
after(() => child?.kill('SIGTERM'));

test('serves the UI and non-secret provider status', async () => {
  const page = await fetch(origin);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /Prometheus — Kişisel Asistan/);
  const status = await fetch(`${origin}/api/status`).then(r => r.json());
  assert.equal(status.provider, 'ollama');
  assert.equal(status.model, 'test-model');
  assert.equal('apiKey' in status, false);
});
test('rejects empty chat prompts', async () => {
  const response = await fetch(`${origin}/api/chat`, { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({message:'  '}) });
  assert.equal(response.status, 400);
  assert.match((await response.json()).error, /Komut boş olamaz/);
});
test('rejects oversized chat prompts', async () => {
  const response = await fetch(`${origin}/api/chat`, { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({message:'x'.repeat(8001)}) });
  assert.equal(response.status, 400);
});
test('uses clear failure response when local model is unavailable', async () => {
  const response = await fetch(`${origin}/api/chat`, { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({message:'test'}) });
  assert.equal(response.status, 502);
  assert.match((await response.json()).error, /Model servisine bağlanılamadı/);
});
