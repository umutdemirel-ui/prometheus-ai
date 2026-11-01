import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
const port = Number(process.env.PORT || 4173);
const provider = (process.env.AI_PROVIDER || 'ollama').toLowerCase();
const model = process.env.AI_MODEL || (provider === 'ollama' ? 'llama3.2' : '');
const baseUrl = (process.env.AI_BASE_URL || (provider === 'ollama' ? 'http://127.0.0.1:11434' : 'https://api.openai.com/v1')).replace(/\/$/, '');
const apiKey = process.env.AI_API_KEY || '';
const mime = { '.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml' };

function json(res, status, data) { res.writeHead(status, {'content-type':'application/json; charset=utf-8','cache-control':'no-store'}); res.end(JSON.stringify(data)); }
async function body(req) { let raw=''; for await (const chunk of req) { raw += chunk; if (raw.length > 64_000) throw new Error('İstek çok büyük.'); } return JSON.parse(raw || '{}'); }

const server=createServer(async(req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(req.method==='GET' && url.pathname==='/api/status') return json(res,200,{configured:Boolean(model && (provider==='ollama'||apiKey)),provider,model:model||null,baseUrl:provider==='ollama'?baseUrl:undefined,apiKeyConfigured:provider!=='ollama'&&Boolean(apiKey)});
  if(req.method==='POST' && url.pathname==='/api/test') {
    try { const data=await body(req); const targetModel=String(data.model||model||'').slice(0,120); if(!targetModel) return json(res,400,{error:'Model adı yapılandırılmamış.'});
      if(provider==='ollama'){ const r=await fetch(`${baseUrl}/api/tags`,{signal:AbortSignal.timeout(8000)}); if(!r.ok) throw new Error(`Ollama HTTP ${r.status}`); const d=await r.json(); return json(res,200,{ok:true,models:(d.models||[]).map(x=>x.name),model:targetModel}); }
      if(!apiKey) return json(res,400,{error:'AI_API_KEY ortam değişkeni tanımlı değil.'});
      const r=await fetch(`${baseUrl}/models`,{headers:{Authorization:`Bearer ${apiKey}`},signal:AbortSignal.timeout(10000)}); if(!r.ok) throw new Error(`Sağlayıcı HTTP ${r.status}`); return json(res,200,{ok:true,model:targetModel});
    } catch(e){return json(res,502,{error:e.cause?.code==='ECONNREFUSED'||e.message==='fetch failed'?'Bağlantı kurulamadı. Ollama çalışıyor mu ve adres doğru mu kontrol edin.':`Bağlantı testi başarısız: ${e.message}`});}
  }
  if(req.method==='POST' && url.pathname==='/api/chat') {
    try { const data=await body(req); const prompt=String(data.message||'').trim(); if(!prompt||prompt.length>8000)return json(res,400,{error:'Komut boş olamaz ve 8.000 karakteri aşamaz.'}); if(!model)return json(res,503,{error:'Model adı yapılandırılmamış.'});
      const messages=[{role:'system',content:'Sen Prometheus adlı, Türkçe yanıt veren yardımcı bir asistansın. Bu uygulamada bilgisayar kontrolü veya web araştırma aracı bağlı değil; bunları yapmış gibi iddia etme.'},...(Array.isArray(data.history)?data.history.slice(-10).filter(m=>['user','assistant'].includes(m.role)).map(m=>({role:m.role,content:String(m.content).slice(0,4000)})):[]),{role:'user',content:prompt}];
      let endpoint,headers={'content-type':'application/json'},payload;
      if(provider==='ollama'){endpoint=`${baseUrl}/api/chat`;payload={model,stream:false,messages};}
      else {if(!apiKey)return json(res,503,{error:'AI_API_KEY sunucu ortam değişkeninde tanımlı değil.'});endpoint=`${baseUrl}/chat/completions`;headers.Authorization=`Bearer ${apiKey}`;payload={model,messages,stream:false};}
      const r=await fetch(endpoint,{method:'POST',headers,body:JSON.stringify(payload),signal:AbortSignal.timeout(120000)});const result=await r.json().catch(()=>({}));if(!r.ok)return json(res,502,{error:result.error?.message||result.error||`Model sağlayıcısı HTTP ${r.status}`});const answer=provider==='ollama'?result.message?.content:result.choices?.[0]?.message?.content;if(!answer)return json(res,502,{error:'Model yanıtı boş veya beklenmeyen biçimde.'});return json(res,200,{answer,model});
    }catch(e){const badRequest=e instanceof SyntaxError||e.message==='İstek çok büyük.';return json(res,badRequest?400:e.name==='TimeoutError'?504:502,{error:badRequest?'Geçersiz veya çok büyük istek.':e.name==='TimeoutError'?'Model yanıtı zaman aşımına uğradı.':e.message==='fetch failed'?'Model servisine bağlanılamadı. Sağlayıcının çalıştığını ve adresini kontrol edin.':e.message||'Model isteği başarısız.'});}
  }
  if(url.pathname.startsWith('/api/')) return json(res,404,{error:'API uç noktası bulunamadı.'});
  const requested=decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname);const file=normalize(join(root,requested));if(!file.startsWith(root)){res.writeHead(403);return res.end('Forbidden');}
  try{const stat=await import('node:fs/promises').then(fs=>fs.stat(file));if(!stat.isFile())throw new Error('Not found');res.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream'});createReadStream(file).pipe(res);}catch{res.writeHead(404);res.end('Not found');}
});
server.listen(port,'0.0.0.0',()=>console.log(`Prometheus hazır: http://0.0.0.0:${port} (AI_PROVIDER=${provider})`));
