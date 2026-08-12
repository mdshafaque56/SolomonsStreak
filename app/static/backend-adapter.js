/* Solomon's Streak FastAPI persistence adapter */
(()=>{
 const TOKEN='ss_api_token', keys=['ss2_tasks','ss2_theme','ss2_focus','ss2_sessions','ss2_discussions','ss2_people','ss2_chats','ss2_profile'];
 const token=()=>localStorage.getItem(TOKEN);
 async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(token())headers.Authorization='Bearer '+token();const r=await fetch('/api'+path,{...options,headers});if(!r.ok)throw new Error((await r.json().catch(()=>({detail:r.statusText}))).detail||'Request failed');return r.status===204?null:r.json()}
 function snapshot(){const p={};for(const k of keys){let v=localStorage.getItem(k);try{p[k]=JSON.parse(v)}catch{p[k]=v}}return p}
 function restore(p){for(const k of keys)if(p&&p[k]!==undefined)localStorage.setItem(k,typeof p[k]==='string'?p[k]:JSON.stringify(p[k]))}
 async function pull(){if(!token())return;try{const p=await api('/state');if(Object.keys(p).length){restore(p);sessionStorage.setItem('ss_api_pulled','1')}}catch(e){console.warn('State pull:',e.message)}}
 let last='';async function push(){if(!token())return;const p=snapshot(),encoded=JSON.stringify(p);if(encoded===last)return;last=encoded;try{await api('/state',{method:'PUT',body:JSON.stringify({payload:p})})}catch(e){console.warn('State push:',e.message)}}
 document.addEventListener('submit',async e=>{
   if(e.target.id!=='loginForm')return;e.preventDefault();e.stopImmediatePropagation();
   const form=e.target,email=form.querySelector('input[type=email]').value.trim(),password=form.querySelector('input[type=password]').value,name=form.querySelector('#loginName').value.trim();
   try{const result=await api('/auth/login',{method:'POST',body:JSON.stringify({email,password,display_name:name,auto_create:true})});localStorage.setItem(TOKEN,result.access_token);localStorage.setItem('ss2_login','1');localStorage.setItem('ss2_user',result.user.display_name);localStorage.setItem('ss2_admin',result.user.role==='owner'?'1':'0');await pull();location.reload()}catch(err){alert(err.message)}
 },true);
 document.addEventListener('click',async e=>{if(!e.target.closest('#logout,#mobileLogout'))return;try{await api('/auth/logout',{method:'POST'})}catch{}localStorage.removeItem(TOKEN)},true);
 window.SolomonAPI={api,pull,push,token};
 if(token()){pull().then(()=>setInterval(push,1200));document.addEventListener('visibilitychange',()=>{if(document.hidden)push()});window.addEventListener('beforeunload',push)}
})();
