import '@testing-library/jest-dom/vitest';
import React from 'react';
import {test,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
const mocks=vi.hoisted(()=>({signUp:vi.fn(async()=>({data:{session:null},error:null}))}));
vi.mock('@supabase/supabase-js',()=>({createClient:()=>({auth:{getSession:async()=>({data:{session:null}}),onAuthStateChange:()=>({data:{subscription:{unsubscribe(){}}}}),signUp:mocks.signUp}})}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.unstubAllEnvs();vi.resetModules();mocks.signUp.mockClear()});
test('email sign-up redirects to the current application origin',async()=>{
 vi.stubEnv('VITE_SUPABASE_URL','https://example.supabase.co');vi.stubEnv('VITE_SUPABASE_ANON_KEY','public-test');localStorage.clear();
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({ollama:false,models:[],openaiConfigured:false})})));
 const {App}=await import('../src/main.jsx');render(<App/>);fireEvent.click(screen.getAllByRole('button',{name:'Ayarlar'})[0]);fireEvent.change(screen.getByPlaceholderText('E-posta'),{target:{value:'person@example.com'}});fireEvent.change(screen.getByPlaceholderText('Şifre'),{target:{value:'password123'}});fireEvent.click(screen.getByRole('button',{name:'Hesap oluştur'}));
 await waitFor(()=>expect(mocks.signUp).toHaveBeenCalledOnce());expect(mocks.signUp.mock.calls[0][0].options.emailRedirectTo).toBe(window.location.origin);expect(await screen.findByText(/E-posta doğrulama bağlantısını kontrol edin/)).toBeInTheDocument();
});
