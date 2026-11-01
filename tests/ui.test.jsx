import "@testing-library/jest-dom/vitest";
import React from 'react';
import {test,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import {App} from '../src/main.jsx';
beforeEach(()=>{localStorage.clear();vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({ollama:false,models:[],openaiConfigured:false})})));});
afterEach(()=>{cleanup();vi.unstubAllGlobals()});
test('navigates from home to research and exposes source limitation',async()=>{
 render(<App/>);expect(screen.getByText('Birlikte neler başarabiliriz?')).toBeTruthy();fireEvent.click(screen.getByRole('button',{name:/Bir konuyu araştır/i}));expect(screen.getByText(/yalnızca Vikipedi sonuçlarını inceler/)).toBeTruthy();
});
test('appearance settings persist and restore after remount',async()=>{
 const view=render(<App/>);fireEvent.click(screen.getAllByRole('button',{name:'Ayarlar'})[0]);fireEvent.change(screen.getByDisplayValue('Koyu'),{target:{value:'light'}});await waitFor(()=>expect(JSON.parse(localStorage.getItem('prometheus-settings')).theme).toBe('light'));view.unmount();render(<App/>);fireEvent.click(screen.getAllByRole('button',{name:'Ayarlar'})[0]);expect(screen.getByDisplayValue('Açık')).toBeTruthy();
});
test('asks for model before attempting a chat',async()=>{
 render(<App/>);const field=screen.getByPlaceholderText(/bir şey sor veya komut ver/);fireEvent.change(field,{target:{value:'Merhaba'}});fireEvent.keyDown(field,{key:'Enter'});expect(await screen.findByRole('alert')).toHaveTextContent('model seçin');
});
test('multiple turns update a single local conversation instead of duplicating snapshots',async()=>{
 localStorage.setItem('prometheus-settings',JSON.stringify({model:'test:1'}));
 Element.prototype.scrollIntoView=vi.fn();
 vi.stubGlobal('fetch',vi.fn(async(url)=>url==='/api/chat'?{ok:true,json:async()=>({content:'Yanıt'})}:{ok:true,json:async()=>({ollama:true,models:['test:1'],openaiConfigured:false})}));
 render(<App/>);
 let field=screen.getByPlaceholderText(/bir şey sor veya komut ver/);fireEvent.change(field,{target:{value:'İlk soru'}});fireEvent.keyDown(field,{key:'Enter'});
 await screen.findByText('Yanıt');field=screen.getByPlaceholderText('Mesajını buraya yaz...');fireEvent.change(field,{target:{value:'İkinci soru'}});fireEvent.keyDown(field,{key:'Enter'});
 await waitFor(()=>expect(JSON.parse(localStorage.getItem('prometheus-history'))?.[0]?.messages?.length).toBe(4));
 expect(JSON.parse(localStorage.getItem('prometheus-history'))).toHaveLength(1);
});
test('local helper is disabled unless the server explicitly enables it',async()=>{
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Araçlar'}));expect(screen.getByText(/Yalnızca kendi bilgisayarındaki yerel kurulumda kullan/)).toBeTruthy();expect(screen.getByRole('button',{name:'İşlemi iste'})).toBeDisabled();
});
test('model proposal must be manually transferred and executed after review',async()=>{
 localStorage.setItem('prometheus-settings',JSON.stringify({model:'test:1'}));
 const fake=vi.fn(async(url)=>url==='/api/desktop/plan'?{ok:true,json:async()=>({action:'list',path:'docs'})}:url==='/api/desktop/execute'?{ok:true,json:async()=>({kind:'list',entries:[],truncated:false})}:{ok:true,json:async()=>({ollama:true,models:['test:1'],openaiConfigured:false,desktopHelperEnabled:true})});vi.stubGlobal('fetch',fake);
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Araçlar'}));fireEvent.change(screen.getByPlaceholderText('Örn. notlar klasörünü listele'),{target:{value:'Belgeleri listele'}});await waitFor(()=>expect(screen.getByRole('button',{name:/AI ile planla/})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:/AI ile planla/}));
 fireEvent.click(await screen.findByRole('button',{name:'Bu planı forma aktar'}));expect(screen.getByDisplayValue('docs')).toBeTruthy();expect(fake.mock.calls.filter(([url])=>url==='/api/desktop/execute')).toHaveLength(0);
 fireEvent.change(screen.getByPlaceholderText(/oturuma özel anahtar/),{target:{value:'a'.repeat(64)}});fireEvent.click(screen.getByRole('button',{name:'İşlemi iste'}));await screen.findByText('Klasör boş.');expect(fake.mock.calls.filter(([url])=>url==='/api/desktop/execute')).toHaveLength(1);
});
