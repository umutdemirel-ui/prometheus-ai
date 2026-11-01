import '@testing-library/jest-dom/vitest';
import React from 'react';
import {test,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
vi.mock('@supabase/supabase-js',()=>({createClient:()=>({
 auth:{getSession:async()=>({data:{session:{user:{id:'u1',email:'test@example.com'}}}}),onAuthStateChange:()=>({data:{subscription:{unsubscribe(){}}}})},
 from:()=>({select:()=>({order:async()=>({data:[{id:'m1',content:'Türkçe tercih ederim',created_at:'2026-01-01'}],error:null})})})
})}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.unstubAllEnvs();vi.resetModules()});
test('selected memory is sent only after explicit consent and can be disabled',async()=>{
 vi.stubEnv('VITE_SUPABASE_URL','https://example.supabase.co');vi.stubEnv('VITE_SUPABASE_ANON_KEY','public-test');localStorage.clear();localStorage.setItem('prometheus-settings',JSON.stringify({model:'test:1'}));
 Element.prototype.scrollIntoView=vi.fn();const confirm=vi.fn(()=>true);vi.stubGlobal('confirm',confirm);
 const fetchMock=vi.fn(async(url)=>url==='/api/chat'?{ok:true,json:async()=>({content:'Yanıt'})}:{ok:true,json:async()=>({ollama:true,models:['test:1'],openaiConfigured:false})});vi.stubGlobal('fetch',fetchMock);
 const {App}=await import('../src/main.jsx');render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Hafıza Merkezi'}));await screen.findByText('Türkçe tercih ederim');
 expect(screen.getByText('Sohbette hafıza kullanımı: Kapalı')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('checkbox',{name:/Sohbete eklemek için seç/}));fireEvent.click(screen.getByRole('button',{name:/Seçilenleri sohbette kullan/}));expect(confirm).toHaveBeenCalledOnce();expect(screen.getByText('Sohbette hafıza kullanımı: Açık')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Sohbet'}));const input=screen.getByPlaceholderText('Mesajını buraya yaz...');fireEvent.change(input,{target:{value:'Merhaba'}});fireEvent.keyDown(input,{key:'Enter'});await screen.findByText('Yanıt');
 const first=fetchMock.mock.calls.find(([url])=>url==='/api/chat');expect(JSON.parse(first[1].body).memories).toEqual(['Türkçe tercih ederim']);
 fireEvent.click(screen.getByRole('button',{name:/1 hafıza aktif · Kapat/}));fireEvent.change(input,{target:{value:'Tekrar'}});fireEvent.keyDown(input,{key:'Enter'});
 await waitFor(()=>expect(fetchMock.mock.calls.filter(([url])=>url==='/api/chat')).toHaveLength(2));const second=fetchMock.mock.calls.filter(([url])=>url==='/api/chat')[1];expect(JSON.parse(second[1].body)).not.toHaveProperty('memories');
});
test('voice result uses current consent, not consent captured when listening started',async()=>{
 vi.stubEnv('VITE_SUPABASE_URL','https://example.supabase.co');vi.stubEnv('VITE_SUPABASE_ANON_KEY','public-test');localStorage.clear();localStorage.setItem('prometheus-settings',JSON.stringify({model:'test:1',voice:false}));Element.prototype.scrollIntoView=vi.fn();vi.stubGlobal('confirm',()=>true);
 let recognizer;class Recognition {constructor(){recognizer=this}start(){this.onstart()}stop(){this.onend()}}vi.stubGlobal('SpeechRecognition',Recognition);
 const fetchMock=vi.fn(async(url)=>url==='/api/chat'?{ok:true,json:async()=>({content:'Sesli yanıt'})}:{ok:true,json:async()=>({ollama:true,models:['test:1'],openaiConfigured:false})});vi.stubGlobal('fetch',fetchMock);
 const {App}=await import('../src/main.jsx');render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Hafıza Merkezi'}));await screen.findByText('Türkçe tercih ederim');fireEvent.click(screen.getByRole('checkbox',{name:/Sohbete eklemek için seç/}));fireEvent.click(screen.getByRole('button',{name:/Seçilenleri sohbette kullan/}));
 fireEvent.click(screen.getByRole('button',{name:'Sohbet'}));fireEvent.click(screen.getByRole('button',{name:'Sesli giriş'}));fireEvent.click(screen.getByRole('button',{name:/1 hafıza aktif · Kapat/}));
 recognizer.onresult({results:[[{transcript:'Sesli mesaj'}]]});
 await waitFor(()=>expect(fetchMock.mock.calls.filter(([url])=>url==='/api/chat')).toHaveLength(1));const call=fetchMock.mock.calls.find(([url])=>url==='/api/chat');expect(JSON.parse(call[1].body)).not.toHaveProperty('memories');
});
