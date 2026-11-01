import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm,access} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {stageDesktopApp,npmInstallCommand} from '../scripts/stage-desktop.mjs';
test('desktop packaging stages an allowlist and lockfile, not env or repository',async()=>{
 const tmp=await mkdtemp(path.join(os.tmpdir(),'prometheus-stage-test-'));const root=path.join(tmp,'root'),stage=path.join(tmp,'stage');
 try{await mkdir(root);await mkdir(stage);for(const dir of ['desktop','desktop-helper','server','dist']){await mkdir(path.join(root,dir));await writeFile(path.join(root,dir,'file.txt'),dir)}
 await writeFile(path.join(root,'package.json'),JSON.stringify({name:'demo',version:'1.0.0',dependencies:{express:'^4.21.2'}}));await writeFile(path.join(root,'package-lock.json'),'{"lockfileVersion":3}');await writeFile(path.join(root,'.env'),'DO_NOT_COPY=secret');await mkdir(path.join(root,'.git'));
 await stageDesktopApp(root,stage);assert.equal(JSON.parse(await readFile(path.join(stage,'package.json'),'utf8')).main,'desktop/main.js');assert.equal(await readFile(path.join(stage,'package-lock.json'),'utf8'),'{"lockfileVersion":3}');
 await assert.rejects(()=>access(path.join(stage,'.env')));await assert.rejects(()=>access(path.join(stage,'.git')));assert.equal(await readFile(path.join(stage,'server','file.txt'),'utf8'),'server');
 }finally{await rm(tmp,{recursive:true,force:true})}
});
test('packaging uses npm CLI through node on Windows and lockfile installation',()=>{
 const a=npmInstallCommand({platform:'win32',npmExecPath:'C:\\npm\\npm-cli.js',nodePath:'C:\\node\\node.exe'});assert.equal(a.command,'C:\\node\\node.exe');assert.deepEqual(a.args.slice(0,3),['C:\\npm\\npm-cli.js','ci','--omit=dev']);
 const b=npmInstallCommand({platform:'win32',npmExecPath:'',comspec:'cmd.exe'});assert.deepEqual(b.args.slice(0,5),['/d','/s','/c','npm.cmd','ci']);
});
