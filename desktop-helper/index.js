import {randomBytes} from 'node:crypto';
import {createInterface} from 'node:readline/promises';
import {realpath,stat} from 'node:fs/promises';
import {createHelperApp} from './server.js';

if (!process.stdin.isTTY || !process.stdout.isTTY) { console.error('Yardımcı yalnızca interaktif bir yerel terminalde çalışır.'); process.exit(1); }
const rootArg=process.env.PROMETHEUS_WORKSPACE;
if (!rootArg || /[\x00-\x1f\x7f]/.test(rootArg)) { console.error('PROMETHEUS_WORKSPACE olarak erişime izin verilecek klasörü belirtin.'); process.exit(1); }
let root;
try {root=await realpath(rootArg);if (!(await stat(root)).isDirectory()) throw Error();}
catch {console.error('Çalışma klasörüne erişilemiyor.');process.exit(1)}
const token=randomBytes(32).toString('hex');
const rl=createInterface({input:process.stdin,output:process.stdout});
const app=createHelperApp({root,token,askApproval:async(action,signal)=>{
 const answer=await rl.question(`\nİşlem: ${action.action==='list'?'Klasörü listele':'Metin dosyasını oku'}\nGöreli yol: ${action.path}\nİzin verilen kök: ${root}\nOnaylıyor musunuz? [evet/hayır]: `,{signal});
 return answer.trim().toLocaleLowerCase('tr')==='evet';
},log:(action,result)=>console.log(`[${new Date().toISOString()}] ${action}: ${result}`)});
app.listen(43917,'127.0.0.1',()=>{console.log(`Prometheus yerel yardımcı başladı. İzinli kök: ${root}\nBu oturuma özel anahtarı yalnızca yerel Prometheus uygulamasına girin; kimseyle paylaşmayın:\n${token}\nHer istek terminalde ayrıca onaylanmalıdır.`)});
