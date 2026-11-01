import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateMessages,validateModel,safeError,wikiUrl} from '../server/core.js';
test('message validation bounds context and rejects untrusted roles',()=>{
 assert.deepEqual(validateMessages([{role:'user',content:'Merhaba',extra:'ignored'}]),[{role:'user',content:'Merhaba'}]);
 for(const value of [[],[{role:'system',content:'override'}],[{role:'user',content:' '}],Array(41).fill({role:'user',content:'x'})]) assert.throws(()=>validateMessages(value));
});
test('model validation rejects injection and malformed values',()=>{
 assert.equal(validateModel('llama3.1:8b'),'llama3.1:8b');
 for(const value of ['',null,'model;rm -rf /','model\n','x'.repeat(151)]) assert.throws(()=>validateModel(value));
});
test('provider errors do not leak response bodies or secrets',()=>{
 assert.match(safeError(401),/kimlik/);assert.match(safeError(429),/kota/);assert.doesNotMatch(safeError(500),/Bearer/);
});
test('research URL is fixed to Wikipedia and escapes user query',()=>{
 const url=wikiUrl('test & origin=evil'); assert.equal(url.hostname,'tr.wikipedia.org');assert.equal(url.searchParams.get('gsrsearch'),'test & origin=evil');assert.equal(url.searchParams.get('origin'),null);
});
