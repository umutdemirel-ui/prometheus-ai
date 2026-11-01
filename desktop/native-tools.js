import path from 'node:path';
import {realpath,stat} from 'node:fs/promises';
import {validateAction,executeTool} from '../desktop-helper/tools.js';

// The renderer can request an operation but cannot select a filesystem root by path.
// Only the native picker callback may grant a root; each operation requires a dialog.
export function createNativeTools({selectDirectory,confirmAction,execute=executeTool}) {
 let root=null,busy=false,generation=0;
 return {
  async chooseDirectory(){
   if(busy)throw new Error('Önce devam eden işlemi tamamlayın.');
   busy=true;const grantGeneration=generation;
   try {const selected=await selectDirectory();if(!selected||grantGeneration!==generation)return null;
    const resolved=await realpath(selected);if(!(await stat(resolved)).isDirectory())throw new Error('Klasör açılamadı.');
    if(grantGeneration!==generation)return null;root=resolved;return {name:path.basename(root)||root};
   } finally {busy=false}
  },
  async run(input){
   if(busy)throw new Error('Başka bir işlem sürüyor.');
   if(!root)throw new Error('Önce yerel bir klasör seçin.');
   const action=validateAction(input);const approvedRoot=root;busy=true;
   try{
    if(!await confirmAction({root:approvedRoot,...action}))return {cancelled:true};
    if(root!==approvedRoot)throw new Error('İzinli klasör değişti.');
    try{return await execute(approvedRoot,action)}catch{throw new Error('İşlem gerçekleştirilemedi. Yol ve dosya izinlerini kontrol edin.')}
   }finally{busy=false}
  },
  clear(){generation++;root=null}
 };
}
