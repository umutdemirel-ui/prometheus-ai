import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import http from 'node:http';
import {once} from 'node:events';
let mock, child, base, receivedChat;
before(async()=>{
 mock=http.createServer((req,res)=>{res.setHeader('content-type','application/json');if(req.url==='/api/tags')res.end(JSON.stringify({models:[{name:'test:1'}]}));else if(req.url==='/api/chat'){let raw='';req.on('data',chunk=>raw+=chunk);req.on('end',()=>{receivedChat=JSON.parse(raw);const prompt=receivedChat.messages?.at(-1)?.content;const content=receivedChat.format==='json'?(prompt==='zararlı'?JSON.stringify({action:'read',path:'../secret'}):JSON.stringify({action:'list',path:'docs'})):'Merhaba!';res.end(JSON.stringify({message:{content}}))})}else {res.statusCode=404;res.end('{}')}}).listen(0,'127.0.0.1');await once(mock,'listening');
 const probe=http.createServer().listen(0,'127.0.0.1');await once(probe,'listening');const port=probe.address().port;await new Promise(r=>probe.close(r));base=`http://127.0.0.1:${port}`;
 child=spawn(process.execPath,['server/index.js'],{env:{...process.env,PORT:String(port),OLLAMA_URL:`http://127.0.0.1:${mock.address().port}`,OPENAI_API_KEY:''},stdio:['ignore','pipe','pipe']});
 await Promise.race([once(child.stdout,'data'),new Promise((_,reject)=>setTimeout(()=>reject(Error('server timeout')),5000))]);
});
after(()=>{child?.kill();mock?.close()});
test('status uses actual mock Ollama model list',async()=>{const d=await (await fetch(base+'/api/status')).json();assert.equal(d.ollama,true);assert.deepEqual(d.models,['test:1']);assert.equal(d.openaiConfigured,false)});
test('chat sends valid requests and handles unsupported providers',async()=>{
 const chat=body=>fetch(base+'/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
 const r=await chat({model:'test:1',provider:'ollama',messages:[{role:'user',content:'Merhaba'}]});assert.equal(r.status,200);assert.equal((await r.json()).content,'Merhaba!');
 assert.equal((await chat({model:'test:1',provider:'other',messages:[{role:'user',content:'a'}]})).status,400);
 assert.equal((await chat({model:'test:1',provider:'openai',messages:[{role:'user',content:'a'}]})).status,400);
 assert.equal((await chat({model:'test:1',provider:'ollama',messages:[{role:'system',content:'a'}]})).status,400);
});
test('cross-origin requests and invalid research are rejected',async()=>{
 assert.equal((await fetch(base+'/api/status',{headers:{origin:'https://evil.example'}})).status,403);
 const r=await fetch(base+'/api/research',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({query:'x'})});assert.equal(r.status,400);
});

test('only explicit valid memories reach the mock provider',async()=>{
 const chat=memories=>fetch(base+'/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({provider:'ollama',model:'test:1',messages:[{role:'user',content:'Merhaba'}],...(memories===undefined?{}:{memories})})});
 assert.equal((await chat(undefined)).status,200);assert.equal(receivedChat.messages.length,1);assert.equal(receivedChat.messages[0].role,'user');
 assert.equal((await chat(['Türkçe yanıtları tercih ederim.'])).status,200);assert.equal(receivedChat.messages[0].role,'system');assert.match(receivedChat.messages[0].content,/Türkçe yanıtları/);
 assert.equal((await chat(Array(6).fill('a'))).status,400);
});

test('desktop helper gateway is disabled by default',async()=>{
 const response=await fetch(base+'/api/desktop/execute',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action:'list',path:'.'})});assert.equal(response.status,403);assert.match((await response.json()).error,/devre dışı/);
});

test('enabled planner validates mock model output without executing a tool',async()=>{
 const probe=http.createServer().listen(0,'127.0.0.1');await once(probe,'listening');const port=probe.address().port;await new Promise(r=>probe.close(r));
 const enabled=spawn(process.execPath,['server/index.js'],{env:{...process.env,PORT:String(port),ENABLE_DESKTOP_HELPER:'true',OLLAMA_URL:`http://127.0.0.1:${mock.address().port}`,OPENAI_API_KEY:''},stdio:['ignore','pipe','pipe']});
 try{await Promise.race([once(enabled.stdout,'data'),new Promise((_,reject)=>setTimeout(()=>reject(Error('server timeout')),5000))]);
 const plan=prompt=>fetch(`http://127.0.0.1:${port}/api/desktop/plan`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({model:'test:1',provider:'ollama',prompt})});
 const r=await plan('docs klasörünü listele');assert.equal(r.status,200);assert.deepEqual(await r.json(),{action:'list',path:'docs'});assert.equal(receivedChat.format,'json');
 const bad=await plan('zararlı');assert.equal(bad.status,502);assert.match((await bad.json()).error,/güvenlik/);
 }finally{enabled.kill()}
});
