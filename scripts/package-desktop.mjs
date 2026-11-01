import {packager} from '@electron/packager';
import {mkdtemp,rm} from 'node:fs/promises';
import {stageDesktopApp,npmInstallCommand} from './stage-desktop.mjs';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import path from 'node:path';
import os from 'node:os';
const require=createRequire(import.meta.url);
const args=Object.fromEntries(process.argv.slice(2).map(a=>a.replace(/^--/,'').split('=')));
const platform=args.platform || process.platform, arch=args.arch || process.arch;
if(!['linux','darwin','win32'].includes(platform)||!['x64','arm64'].includes(arch))throw new Error('Desteklenen platform: linux, darwin, win32; mimari: x64, arm64.');
const root=process.cwd();const stage=await mkdtemp(path.join(os.tmpdir(),'prometheus-package-'));
try{
 await stageDesktopApp(root,stage);
 const npm=npmInstallCommand();
 const result=spawnSync(npm.command,npm.args,{cwd:stage,stdio:'inherit'});
 if(result.error || result.status!==0)throw new Error('Paket bağımlılıkları kurulamadı.');
 const paths=await packager({dir:stage,out:path.join(root,'release'),overwrite:true,platform,arch,asar:true,prune:false,executableName:'Prometheus',name:'Prometheus',appBundleId:'ai.prometheus.assistant',electronVersion:require('electron/package.json').version,extendInfo:{NSMicrophoneUsageDescription:'Prometheus, sesli komutları algılamak için mikrofon izni ister.'}});
 console.log('Masaüstü uygulaması:',paths.join(', '));
} catch(error) {console.error('Masaüstü paketi oluşturulamadı:',error.message,'Electron ikilisinin indirilmesi ve platform bağımlılıkları için ağ erişimini kontrol edin.');process.exitCode=1} finally {await rm(stage,{recursive:true,force:true})}
