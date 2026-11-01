import path from 'node:path';
import {constants} from 'node:fs';
import {lstat, realpath, readdir, open} from 'node:fs/promises';
import {TextDecoder} from 'node:util';

export const MAX_TEXT_BYTES = 64 * 1024;
export function validateAction(input) {
  if (!input || typeof input !== 'object' || !['list','read'].includes(input.action)) throw new Error('Desteklenmeyen işlem.');
  const relative = input.path;
  if (typeof relative !== 'string' || relative.length > 512 || /[\x00-\x1f\x7f]/.test(relative) || path.isAbsolute(relative) || path.win32.isAbsolute(relative) || relative.split(/[\\/]/).includes('..')) throw new Error('Geçersiz göreli yol.');
  if (process.platform !== 'win32' && relative.includes('\\')) throw new Error('Geçersiz göreli yol.');
  return {action: input.action, path: relative || '.'};
}
export async function resolveInside(root, relative) {
  const canonicalRoot = await realpath(root);
  const target = path.resolve(canonicalRoot, relative);
  const sub = path.relative(canonicalRoot,target);
  if (sub.startsWith('..'+path.sep) || sub === '..' || path.isAbsolute(sub)) throw new Error('Yol izin verilen klasörün dışında.');
  // Refuse all symlinks, including links that currently point back inside the root.
  let current=canonicalRoot;
  for (const part of sub.split(path.sep).filter(Boolean)) {
    current=path.join(current,part);
    if ((await lstat(current)).isSymbolicLink()) throw new Error('Sembolik bağlantılara izin verilmiyor.');
  }
  const canonicalTarget=await realpath(target);
  const finalSub=path.relative(canonicalRoot,canonicalTarget);
  if (finalSub.startsWith('..'+path.sep) || finalSub==='..' || path.isAbsolute(finalSub)) throw new Error('Yol izin verilen klasörün dışında.');
  return canonicalTarget;
}
export async function executeTool(root, input) {
  const action=validateAction(input);
  const target=await resolveInside(root,action.path);
  if (action.action==='list') {
    if (!(await lstat(target)).isDirectory()) throw new Error('Yol bir klasör değil.');
    const entries=await readdir(target,{withFileTypes:true});
    return {kind:'list',entries:entries.slice(0,200).map(e=>({name:e.name,type:e.isSymbolicLink()?'link':e.isDirectory()?'directory':e.isFile()?'file':'other'})),truncated:entries.length>200};
  }
  // O_NOFOLLOW is not available on all platforms. Recheck immediately before opening.
  if (!(await lstat(target)).isFile()) throw new Error('Yol normal bir dosya değil.');
  const noFollow=constants.O_NOFOLLOW || 0;
  const nonBlock=constants.O_NONBLOCK || 0;
  const file=await open(target,constants.O_RDONLY | noFollow | nonBlock);
  try {
    const stat=await file.stat();
    if (!stat.isFile()) throw new Error('Yol normal bir dosya değil.');
    if (stat.size>MAX_TEXT_BYTES) throw new Error('Dosya 64 KB sınırını aşıyor.');
    const buffer=Buffer.alloc(MAX_TEXT_BYTES+1);
    const {bytesRead}=await file.read(buffer,0,buffer.length,0);
    if (bytesRead>MAX_TEXT_BYTES) throw new Error('Dosya 64 KB sınırını aşıyor.');
    if (buffer.subarray(0,bytesRead).includes(0)) throw new Error('İkili dosyalar okunamaz.');
    try { return {kind:'read',content:new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,bytesRead)),bytes:bytesRead}; }
    catch { throw new Error('Dosya UTF-8 metni değil.'); }
  } finally { await file.close(); }
}
