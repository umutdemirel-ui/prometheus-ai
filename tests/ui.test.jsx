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
