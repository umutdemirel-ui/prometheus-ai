import {test,after,before} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,mkdir,symlink,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {once} from 'node:events';
import {validateAction,executeTool} from '../desktop-helper/tools.js';
import {createHelperApp} from '../desktop-helper/server.js';
import {spawnSync} from 'node:child_process';
let root,outside;
before(async()=>{root=await mkdtemp(path.join(os.tmpdir(),'prometheus-'));outside=await mkdtemp(path.join(os.tmpdir(),'outside-'));await mkdir(path.join(root,'folder'));await writeFile(path.join(root,'folder','test.txt'),'Merhaba Dünya');await writeFile(path.join(outside,'secret.txt'),'gizli');await writeFile(path.join(root,'binary'),Buffer.from([0,1,2]));await writeFile(path.join(root,'big'),Buffer.alloc(65537,'a'));});
after(async()=>{await rm(root,{recursive:true,force:true});await rm(outside,{recursive:true,force:true})});
test('only supported actions and confined relative paths are accepted',()=>{
 assert.deepEqual(validateAction({action:'list',path:''}),{action:'list',path:'.'});
 for(const item of [{action:'shell',path:'.'},{action:'read',path:'../secret'},{action:'read',path:'/etc/passwd'},{action:'read',path:'C:\\Windows'},{action:'list',path:'a\x1b[31m'},{action:'read',path:'a/../b'}]) assert.throws(()=>validateAction(item));
});
test('reads bounded UTF-8 files and lists only selected directory',async()=>{
 const result=await executeTool(root,{action:'read',path:'folder/test.txt'});assert.equal(result.content,'Merhaba Dünya');
 const list=await executeTool(root,{action:'list',path:'.'});assert.ok(list.entries.some(x=>x.name==='folder'&&x.type==='directory'));
 await assert.rejects(()=>executeTool(root,{action:'read',path:'binary'}),/İkili/);await assert.rejects(()=>executeTool(root,{action:'read',path:'big'}),/64 KB/);await assert.rejects(()=>executeTool(root,{action:'read',path:'folder'}),/normal bir dosya/);
});
test('symlink escapes and links to inside the root are rejected',async(t)=>{
 try{await symlink(outside,path.join(root,'escape'),'dir');await symlink(path.join(root,'folder'),path.join(root,'internal-link'),'dir')}catch(e){if(e.code==='EPERM'){t.skip('Symlink creation not permitted');return}throw e}
 await assert.rejects(()=>executeTool(root,{action:'read',path:'escape/secret.txt'}),/Sembolik/);
 await assert.rejects(()=>executeTool(root,{action:'read',path:'internal-link/test.txt'}),/Sembolik/);
});
test('helper requires a token and separately asks for approval',async()=>{
 const token='a'.repeat(64);let approvals=0;let decision=false;
 const app=createHelperApp({root,token,askApproval:async()=>{approvals++;return decision}});const server=app.listen(0,'127.0.0.1');await once(server,'listening');const url=`http://127.0.0.1:${server.address().port}/execute`;
 const send=(key,body)=>fetch(url,{method:'POST',headers:{'content-type':'application/json','x-prometheus-helper-token':key},body:JSON.stringify(body)});
 try {assert.equal((await send('b'.repeat(64),{action:'read',path:'folder/test.txt'})).status,401);assert.equal(approvals,0);
 assert.equal((await send(token,{action:'read',path:'../secret'})).status,400);assert.equal(approvals,0);
 assert.equal((await send(token,{action:'read',path:'folder/test.txt'})).status,403);assert.equal(approvals,1);
 decision=true;const r=await send(token,{action:'read',path:'folder/test.txt'});assert.equal(r.status,200);assert.equal((await r.json()).content,'Merhaba Dünya');assert.equal(approvals,2);
 } finally {await new Promise(resolve=>server.close(resolve))}
});
test('desktop helper refuses non-interactive execution',()=>{
 const run=spawnSync(process.execPath,['desktop-helper/index.js'],{encoding:'utf8',env:{...process.env,PROMETHEUS_WORKSPACE:root},stdio:['pipe','pipe','pipe']});assert.equal(run.status,1);assert.match(run.stderr,/interaktif/);
});
test('cancelling while approval is pending prevents the file operation',async()=>{
 const token='c'.repeat(64);let started;const entered=new Promise(resolve=>{started=resolve});let released,abortObserved;let executions=0;
 const observed=new Promise(resolve=>{abortObserved=resolve});
 const app=createHelperApp({root,token,execute:async()=>{executions++;return {}},askApproval:async(_action,signal)=>{started();await new Promise(resolve=>{released=resolve;signal.addEventListener('abort',()=>{abortObserved();resolve()},{once:true})});return true}});
 const server=app.listen(0,'127.0.0.1');await once(server,'listening');const controller=new AbortController();
 const request=fetch(`http://127.0.0.1:${server.address().port}/execute`,{method:'POST',headers:{'content-type':'application/json','x-prometheus-helper-token':token},body:JSON.stringify({action:'read',path:'folder/test.txt'}),signal:controller.signal});
 try{await entered;controller.abort();await assert.rejects(request,{name:'AbortError'});await observed;await new Promise(resolve=>setImmediate(resolve));assert.equal(executions,0)}finally{released?.();server.closeAllConnections();await new Promise(resolve=>server.close(resolve))}
});
