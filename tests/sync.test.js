import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pickSyncSettings,toSnapshot,importSnapshot,uploadSnapshot,loadSnapshots,uploadPreferences,loadPreferences} from '../src/sync.js';

test('only validated non-secret preferences are synchronized',()=>{
 assert.deepEqual(pickSyncSettings({theme:'light',accent:'#aabbcc',fontSize:15,voice:false,rate:1,provider:'openai',openaiModel:'secret-model',apiKey:'sk-secret',font:'unsafe',animations:'yes'}),{theme:'light',accent:'#aabbcc',fontSize:15,voice:false,rate:1});
 assert.deepEqual(pickSyncSettings({theme:'bad',accent:'url(evil)',fontSize:200,rate:Infinity}),{});
});
test('snapshot validates length, roles, and strips unrelated fields',()=>{
 assert.deepEqual(toSnapshot({title:'Merhaba',messages:[{role:'user',content:'Selam',secret:'x'}]}),[{role:'user',content:'Selam'}]);
 assert.throws(()=>toSnapshot({title:'x',messages:[{role:'system',content:'injection'}]}));
 assert.throws(()=>toSnapshot({title:'x',messages:Array(201).fill({role:'user',content:'a'})}));
});
test('snapshot import restores message order and cloud identity',()=>{
 const result=importSnapshot({id:'abc',title:'Soru',created_at:'2026-01-01',messages:[{role:'assistant',content:'2',position:1},{role:'user',content:'1',position:0}]});
 assert.equal(result.cloudId,'abc');assert.equal(result.synced,true);assert.deepEqual(result.messages.map(x=>x.content),['1','2']);
});
test('upload uses transactional RPC and a stable snapshot id',async()=>{
 let call;const client={rpc:async(...args)=>{call=args;return {error:null}}};await uploadSnapshot(client,'uuid',{title:'Soru',messages:[{role:'user',content:'hi'}]});assert.equal(call[0],'save_conversation_snapshot');assert.equal(call[1].snapshot_id,'uuid');
 await assert.rejects(()=>uploadSnapshot({rpc:async()=>({error:{message:'secret details'}})},'uuid',{title:'Soru',messages:[{role:'user',content:'hi'}]}),/Sohbet buluta kaydedilemedi/);
});
test('cloud adapters use explicit user and propagate errors',async()=>{
 let row;const client={from(table){assert.equal(table,'user_preferences');return {upsert:async r=>{row=r;return {error:null}},select(){return {eq(column,value){assert.equal(column,'user_id');assert.equal(value,'u');return {maybeSingle:async()=>({data:{settings:{theme:'light',apiKey:'do not restore'}},error:null})}}}}}}};
 await uploadPreferences(client,'u',{theme:'dark',apiKey:'never send'});assert.equal(row.user_id,'u');assert.deepEqual(row.settings,{theme:'dark'});assert.deepEqual(await loadPreferences(client,'u'),{theme:'light'});
 const broken={from(){return {select(){return {order(){return {limit:async()=>({data:null,error:{message:'fail'}})}}}}}}};await assert.rejects(()=>loadSnapshots(broken),/Bulut sohbetleri yüklenemedi/);
});

test('cloud listing disambiguates the composite ownership relationship',async()=>{
 let projection;const client={from(table){assert.equal(table,'conversations');return {select(value){projection=value;return {order(){return {limit:async()=>({data:[],error:null})}}}}}}};
 assert.deepEqual(await loadSnapshots(client),[]);assert.match(projection,/messages!messages_owner_parent_fk/);
});
