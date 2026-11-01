import express from 'express';
import {validateMessages, validateModel, safeError, wikiUrl} from './core.js';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const app = express();
app.use(express.json({limit:'512kb'}));
// Reject cross-origin browser requests. Provider addresses are server-controlled, never supplied by clients.
app.use('/api', (req,res,next) => {
  const origin = req.get('origin');
  if (origin && origin !== `${req.protocol}://${req.get('host')}`) return res.status(403).json({error:'İstek kaynağına izin verilmiyor.'});
  res.set('Cache-Control','no-store'); next();
});
const ollama = (process.env.OLLAMA_URL || 'http://127.0.0.1:11434').replace(/\/$/,'');
const openai = (process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1').replace(/\/$/,'');
async function request(url, options={}) { return fetch(url, {...options, signal: options.signal || AbortSignal.timeout(15000)}); }
app.get('/api/status', async (req,res) => {
  try {
    const response = await request(`${ollama}/api/tags`);
    if (!response.ok) throw new Error('bad status');
    const data = await response.json();
    res.json({ollama:true, models:(data.models || []).map(x=>x.name), openaiConfigured:!!process.env.OPENAI_API_KEY});
  } catch { res.json({ollama:false, models:[], openaiConfigured:!!process.env.OPENAI_API_KEY}); }
});
app.post('/api/chat', async (req,res) => {
  let messages, model;
  try { messages = validateMessages(req.body.messages); model = validateModel(req.body.model); } catch(e) { return res.status(400).json({error:e.message}); }
  const provider = req.body.provider;
  if (!['ollama','openai'].includes(provider)) return res.status(400).json({error:'Desteklenmeyen sağlayıcı.'});
  if (provider === 'openai' && !process.env.OPENAI_API_KEY) return res.status(400).json({error:'Sunucuda OPENAI_API_KEY yapılandırılmamış.'});
  const controller = new AbortController();
  const timeout = setTimeout(()=>controller.abort(), 120000);
  res.on('close', () => controller.abort());
  try {
    const response = await fetch(provider === 'ollama' ? `${ollama}/api/chat` : `${openai}/chat/completions`, {
      method:'POST', signal:controller.signal,
      headers:{'Content-Type':'application/json', ...(provider === 'openai' ? {Authorization:`Bearer ${process.env.OPENAI_API_KEY}`} : {})},
      body:JSON.stringify({model,messages,stream:false})
    });
    if (!response.ok) return res.status(response.status >= 400 && response.status < 600 ? response.status : 502).json({error:safeError(response.status)});
    const data = await response.json();
    const content = provider === 'ollama' ? data.message?.content : data.choices?.[0]?.message?.content;
    if (typeof content !== 'string') throw new Error('invalid response');
    res.json({content});
  } catch(e) { if (!res.headersSent) res.status(502).json({error:e.name === 'AbortError' ? 'İstek iptal edildi veya zaman aşımına uğradı.' : 'Sağlayıcıya ulaşılamadı. Sunucunun çalıştığını ve modelin kurulu olduğunu kontrol edin.'}); }
  finally { clearTimeout(timeout); }
});
app.post('/api/research', async (req,res) => {
  const query = req.body.query;
  if (typeof query !== 'string' || query.trim().length < 3 || query.length > 300) return res.status(400).json({error:'3–300 karakterlik bir konu girin.'});
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  res.on('close', () => controller.abort());
  try {
    const response = await request(wikiUrl(query.trim()), {signal:controller.signal});
    if (!response.ok) throw new Error('search failed');
    const data = await response.json();
    const sources = (data.query?.pages || []).filter(p=>p.extract && p.fullurl).map(p=>({title:p.title,url:p.fullurl,extract:p.extract}));
    res.json({sources});
  } catch { if (!res.headersSent) res.status(502).json({error:'Vikipedi kaynağına ulaşılamadı. İnternet bağlantısını kontrol edin.'}); }
  finally { clearTimeout(timeout); }
});
if (existsSync('dist')) app.use(express.static('dist'));
app.get('*', (req,res) => { if (existsSync('dist/index.html')) res.sendFile(join(process.cwd(),'dist/index.html')); else res.status(404).send('Önce npm run build çalıştırın.'); });
const port = Number(process.env.PORT || 3001);
app.listen(port, '127.0.0.1', () => console.log(`Prometheus API: http://127.0.0.1:${port}`));
