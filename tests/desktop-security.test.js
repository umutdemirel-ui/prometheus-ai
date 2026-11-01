import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sameOrigin,allowMediaCheck,allowAudioRequest,safeExternalUrl,shouldAttachBackendToken,navigationTarget} from '../desktop/security.js';
const origin='http://127.0.0.1:46321';
test('navigation and external links only allow explicit safe URLs',()=>{
 assert.equal(sameOrigin(origin+'/app',origin),true);assert.equal(sameOrigin('https://evil.example',origin),false);assert.equal(sameOrigin('invalid',origin),false);
 assert.equal(safeExternalUrl('https://example.com'),true);for(const url of ['file:///etc/passwd','javascript:alert(1)','http://example.com','invalid']) assert.equal(safeExternalUrl(url),false);
});
test('desktop permissions allow only same-origin audio requests',()=>{
 assert.equal(allowMediaCheck({permission:'media',requestingOrigin:origin,origin,mediaType:'audio'}),true);
 assert.equal(allowMediaCheck({permission:'media',requestingOrigin:'https://evil.example',origin,mediaType:'audio'}),false);
 assert.equal(allowMediaCheck({permission:'media',requestingOrigin:origin,origin,mediaType:'video'}),false);
 assert.equal(allowAudioRequest({permission:'media',pageUrl:origin,origin,mediaTypes:['audio']}),true);
 for(const value of [{permission:'media',pageUrl:origin,origin,mediaTypes:['audio','video']},{permission:'media',pageUrl:origin,requestingUrl:'https://evil.example',origin,mediaTypes:['audio']},{permission:'geolocation',pageUrl:origin,origin,mediaTypes:['audio']},{permission:'media',pageUrl:origin,origin,mediaTypes:[]}])assert.equal(allowAudioRequest(value),false);
});

test('backend token is never attached to cross-origin or subframe requests',()=>{
 const base={url:origin+'/api/status',origin,webContentsId:3,expectedWebContentsId:3,initiatorOrigin:origin,frameIsMain:true};
 assert.equal(shouldAttachBackendToken(base),true);
 for(const bad of [{...base,initiatorOrigin:'https://evil.example'},{...base,frameIsMain:false},{...base,url:'https://evil.example/api/status'},{...base,webContentsId:4},{...base,initiatorOrigin:undefined}])assert.equal(shouldAttachBackendToken(bad),false);
 assert.equal(navigationTarget({url:origin+'/modern'},'https://evil.example'),origin+'/modern');assert.equal(navigationTarget({},origin+'/legacy'),origin+'/legacy');
});
