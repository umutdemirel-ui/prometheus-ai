import {cp,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';

// Stage only application code and the checked-in lockfile, never .env or the repository.
export async function stageDesktopApp(root,stage) {
 for(const dir of ['desktop','desktop-helper','server','dist']) await cp(path.join(root,dir),path.join(stage,dir),{recursive:true});
 const project=JSON.parse(await readFile(path.join(root,'package.json'),'utf8'));
 project.productName='Prometheus';project.main='desktop/main.js';
 await writeFile(path.join(stage,'package.json'),JSON.stringify(project,null,2));
 await cp(path.join(root,'package-lock.json'),path.join(stage,'package-lock.json'));
 return project;
}
export function npmInstallCommand({platform=process.platform,npmExecPath=process.env.npm_execpath,nodePath=process.execPath,comspec=process.env.ComSpec}={}) {
 const args=['ci','--omit=dev','--ignore-scripts','--no-audit','--no-fund'];
 if(npmExecPath) return {command:nodePath,args:[npmExecPath,...args]};
 if(platform==='win32')return {command:comspec||'cmd.exe',args:['/d','/s','/c','npm.cmd',...args]};
 return {command:'npm',args};
}
