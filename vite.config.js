import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],server:{host:'0.0.0.0',allowedHosts:true,proxy:{'/api':{target:'http://127.0.0.1:3001',changeOrigin:true,configure:(proxy)=>{proxy.on('proxyReq',(proxyReq,req)=>{if(req.headers.origin){try{if(new URL(req.headers.origin).host===req.headers.host) proxyReq.setHeader('origin','http://127.0.0.1:3001')}catch{}}})}}}}});
