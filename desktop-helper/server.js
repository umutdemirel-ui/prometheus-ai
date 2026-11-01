import express from 'express';
import {timingSafeEqual} from 'node:crypto';
import {validateAction, executeTool} from './tools.js';

// askApproval must be backed by a local human-controlled terminal in production.
export function createHelperApp({root, token, askApproval, log=()=>{}, execute=executeTool}) {
 const app=express();app.use(express.json({limit:'8kb'}));let busy=false;
 function authorized(value){if(typeof value!=='string'||!/^[a-f0-9]{64}$/.test(value))return false;return timingSafeEqual(Buffer.from(value,'hex'),Buffer.from(token,'hex'))}
 app.post('/execute',async(req,res)=>{
  if(!authorized(req.get('x-prometheus-helper-token')))return res.status(401).json({error:'Yardımcı oturum anahtarı geçersiz.'});
  let action;try{action=validateAction(req.body)}catch(e){return res.status(400).json({error:e.message})}
  if(busy)return res.status(409).json({error:'Başka bir işlem onay bekliyor.'});busy=true;
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),60000);
  res.on('close',()=>controller.abort());
  try {
   const approved=await askApproval(action,controller.signal);
   if(controller.signal.aborted || res.destroyed)return;
   if(!approved)return res.status(403).json({error:'İşlem yerel terminalde reddedildi.'});
   const result=await execute(root,action);
   if(!res.destroyed)res.json(result);
   log(action.action,'tamamlandı');
  } catch(e) {
   if(!res.destroyed)res.status(e.name==='AbortError'?408:400).json({error:e.name==='AbortError'?'Onay zaman aşımı veya iptal.':'İşlem gerçekleştirilemedi. Yol ve dosya izinlerini kontrol edin.'});
   log(action.action,'iptal veya hata');
  } finally {clearTimeout(timeout);busy=false}
 });
 return app;
}
