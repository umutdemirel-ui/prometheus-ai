import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseDesktopPlan} from '../server/desktop-plan.js';
test('planner allows only structured, relative, allowlisted actions',()=>{
 assert.deepEqual(parseDesktopPlan('{"action":"list","path":"docs"}'),{action:'list',path:'docs'});
 assert.deepEqual(parseDesktopPlan('{"action":"unsupported","command":"rm -rf /"}'),{action:'unsupported',message:'Bu istek yerel yardımcı tarafından desteklenmiyor.'});
 for(const text of ['rm -rf /','{"action":"shell","path":"."}','{"action":"read","path":"../secret"}','{"action":"read","path":"/etc/passwd"}','{"action":"read"}', '[]','null']) assert.throws(()=>parseDesktopPlan(text));
});
