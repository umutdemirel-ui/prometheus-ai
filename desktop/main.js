import {app,BrowserWindow,dialog,ipcMain,session,shell,systemPreferences} from 'electron/main';
import {randomBytes} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createApp} from '../server/app.js';
import {createNativeTools} from './native-tools.js';
import {sameOrigin,allowMediaCheck,allowAudioRequest,safeExternalUrl,shouldAttachBackendToken,navigationTarget} from './security.js';

const PORT=46321;
const origin=`http://127.0.0.1:${PORT}`;
const token=randomBytes(32).toString('hex');
const dirname=path.dirname(fileURLToPath(import.meta.url));
let window,server;
const gotLock=app.requestSingleInstanceLock();
if(!gotLock)app.quit();
else {
 app.on('second-instance',()=>{if(window){if(window.isMinimized())window.restore();window.focus()}});
 app.whenReady().then(start).catch(()=>{dialog.showErrorBox('Prometheus','Masaüstü uygulaması başlatılamadı. 46321 portunun boş olduğunu kontrol edin.');app.quit()});
}
async function start(){
 const backend=createApp({apiToken:token,nativeDesktop:true,enableDesktopHelper:false,distPath:path.join(app.getAppPath(),'dist')});
 server=await new Promise((resolve,reject)=>{const instance=backend.listen(PORT,'127.0.0.1',()=>resolve(instance));instance.once('error',reject)});
 const desktopSession=session.fromPartition('persist:prometheus');
 desktopSession.webRequest.onBeforeSendHeaders({urls:[`${origin}/api/*`]},(details,callback)=>{
  if(window && shouldAttachBackendToken({url:details.url,origin,webContentsId:details.webContentsId,expectedWebContentsId:window.webContents.id,initiatorOrigin:details.initiatorOrigin,frameIsMain:details.frame?.frameTreeNodeId===window.webContents.mainFrame.frameTreeNodeId})) details.requestHeaders['X-Prometheus-Desktop-Token']=token;
  callback({requestHeaders:details.requestHeaders});
 });
 desktopSession.setPermissionCheckHandler((wc,permission,requestingOrigin,details={})=>
  wc===window?.webContents && allowMediaCheck({permission,requestingOrigin,origin,mediaType:details.mediaType}));
 desktopSession.setPermissionRequestHandler(async(wc,permission,callback,details={})=>{
  if(wc!==window?.webContents || !allowAudioRequest({permission,pageUrl:wc.getURL(),requestingUrl:details.requestingUrl,origin,mediaTypes:details.mediaTypes}))return callback(false);
  try {
   const result=await dialog.showMessageBox(window,{type:'question',buttons:['İzin verme','Mikrofona izin ver'],defaultId:0,cancelId:0,title:'Mikrofon izni',message:'Prometheus mikrofonu kullanmak istiyor.',detail:'Ses tanıma tarayıcı hizmetine bağlı olabilir. İstediğiniz zaman sistem ayarlarından izni geri alabilirsiniz.'});
   if(result.response!==1)return callback(false);
   if(process.platform==='darwin' && !await systemPreferences.askForMediaAccess('microphone'))return callback(false);
   callback(true);
  } catch {callback(false)}
 });
 window=new BrowserWindow({width:1440,height:900,minWidth:850,minHeight:620,title:'Prometheus',backgroundColor:'#09090c',show:false,webPreferences:{preload:path.join(dirname,'preload.cjs'),session:desktopSession,contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true,webviewTag:false,devTools:false}});
 const tools=createNativeTools({
  selectDirectory:async()=>{const result=await dialog.showOpenDialog(window,{title:'Prometheus için izinli klasörü seç',properties:['openDirectory']});return result.canceled?null:result.filePaths[0]},
  confirmAction:async({root,action,path:relative})=>{const result=await dialog.showMessageBox(window,{type:'question',buttons:['İptal','İzin ver'],defaultId:0,cancelId:0,title:'Yerel dosya işlemi',message:action==='list'?'Klasör içeriği listelensin mi?':'Metin dosyası okunsun mu?',detail:`İzinli klasör: ${root}\nGöreli yol: ${relative}\n\nBu işlem yalnızca seçilen klasörle sınırlıdır.`});return result.response===1}
 });
 function trusted(event){return event.sender===window?.webContents && event.senderFrame?.frameTreeNodeId===window?.webContents.mainFrame.frameTreeNodeId && sameOrigin(event.senderFrame.url,origin)}
 ipcMain.handle('prometheus:choose-directory',event=>{if(!trusted(event))throw new Error('Yetkisiz istek.');return tools.chooseDirectory()});
 ipcMain.handle('prometheus:execute-tool',(event,action)=>{if(!trusted(event))throw new Error('Yetkisiz istek.');return tools.run(action)});
 ipcMain.handle('prometheus:clear-directory',event=>{if(!trusted(event))throw new Error('Yetkisiz istek.');tools.clear()});
 window.webContents.setWindowOpenHandler(({url})=>{if(safeExternalUrl(url))void shell.openExternal(url).catch(()=>{});return {action:'deny'}});
 const guardNavigation=(event,legacyUrl)=>{if(!sameOrigin(navigationTarget(event,legacyUrl),origin))event.preventDefault()};
 window.webContents.on('will-navigate',guardNavigation);
 window.webContents.on('will-redirect',guardNavigation);
 window.webContents.on('will-frame-navigate',guardNavigation);
 window.webContents.on('will-attach-webview',event=>event.preventDefault());
 window.once('ready-to-show',()=>window.show());
 window.on('closed',()=>{tools.clear();window=null});
 await window.loadURL(origin);
}
app.on('window-all-closed',()=>app.quit());
app.on('before-quit',()=>{server?.close()});
