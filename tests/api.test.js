import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import http from 'node:http';
import {once} from 'node:events';
let mock, child, base, receivedChat;
before(async()=>{
 mock=http.createServer((req,res)=>{res.setHeader('content-type','application/json');if(req.url==='/api/tags')res.end(JSON.stringify({models:[{name:'test:1'}]}));else if(req.url==='/api/chat'){let raw='';req.on('data',chunk=>raw+=chunk);req.on('end',()=>{receivedChat=JSON.parse(raw);res.end(JSON.stringify({message:{content:'Merhaba!'}}))})}else {res.statusCode=404;res.end('{}')}}).listen(0,'127.0.0.1');await once(mock,'listening');
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
