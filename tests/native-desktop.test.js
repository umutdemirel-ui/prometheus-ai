import {test,before,after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {once} from 'node:events';
import os from 'node:os';
import path from 'node:path';
import {createNativeTools} from '../desktop/native-tools.js';
import {createApp} from '../server/app.js';
let root;
before(async()=>{root=await mkdtemp(path.join(os.tmpdir(),'prometheus-native-'));await mkdir(path.join(root,'docs'));await writeFile(path.join(root,'docs','note.txt'),'yerel metin')});
after(async()=>{await rm(root,{recursive:true,force:true})});
test('native file access requires directory picker and per-action approval',async()=>{
 let selected=0,approved=0,decision=false;
 const tools=createNativeTools({selectDirectory:async()=>{selected++;return root},confirmAction:async({root:r,action,path:p})=>{approved++;assert.equal(r,root);assert.equal(action,'read');assert.equal(p,'docs/note.txt');return decision}});
 await assert.rejects(()=>tools.run({action:'read',path:'docs/note.txt'}),/Önce/);
 assert.equal((await tools.chooseDirectory()).name,path.basename(root));assert.equal(selected,1);
 await assert.rejects(()=>tools.run({action:'read',path:'../secret'}),/Geçersiz/);assert.equal(approved,0);
 assert.deepEqual(await tools.run({action:'read',path:'docs/note.txt'}),{cancelled:true});assert.equal(approved,1);
 decision=true;assert.equal((await tools.run({action:'read',path:'docs/note.txt'})).content,'yerel metin');assert.equal(approved,2);
 tools.clear();await assert.rejects(()=>tools.run({action:'read',path:'docs/note.txt'}),/Önce/);
});
test('native file access cannot run concurrent approval operations',async()=>{
 let proceed,entered;const wait=new Promise(r=>{entered=r});const tools=createNativeTools({selectDirectory:async()=>root,confirmAction:()=>{entered();return new Promise(r=>{proceed=r})}});
 await tools.chooseDirectory();const pending=tools.run({action:'list',path:'.'});await wait;
 await assert.rejects(()=>tools.run({action:'list',path:'.'}),/Başka/);await assert.rejects(()=>tools.chooseDirectory(),/devam eden/);proceed(false);assert.deepEqual(await pending,{cancelled:true});
});
test('desktop server requires token and preserves cross-origin rejection',async()=>{
 const token='a'.repeat(64);const app=createApp({apiToken:token,nativeDesktop:true,enableDesktopHelper:false});const server=app.listen(0,'127.0.0.1');await once(server,'listening');const origin=`http://127.0.0.1:${server.address().port}`;
 try{
  assert.equal((await fetch(origin+'/api/status')).status,401);
  assert.equal((await fetch(origin+'/api/status',{headers:{'x-prometheus-desktop-token':'b'.repeat(64)}})).status,401);
  assert.equal((await fetch(origin+'/api/status',{headers:{'x-prometheus-desktop-token':token,origin:'https://evil.example'}})).status,403);
  const r=await fetch(origin+'/api/status',{headers:{'x-prometheus-desktop-token':token}});assert.equal(r.status,200);assert.equal((await r.json()).desktopHelperEnabled,true);
  const e=await fetch(origin+'/api/desktop/execute',{method:'POST',headers:{'content-type':'application/json','x-prometheus-desktop-token':token},body:'{}'});assert.equal(e.status,403);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r))}
});
test('revoking permission during folder selection cannot grant it later',async()=>{
 let release,entered;const waiting=new Promise(r=>{entered=r});const tools=createNativeTools({selectDirectory:()=>{entered();return new Promise(r=>{release=r})},confirmAction:async()=>true});
 const choosing=tools.chooseDirectory();await waiting;tools.clear();release(root);assert.equal(await choosing,null);await assert.rejects(()=>tools.run({action:'list',path:'.'}),/Önce/);
});
