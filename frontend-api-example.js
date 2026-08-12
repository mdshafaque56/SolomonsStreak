const API = 'http://localhost:8000/api/v1';
let accessToken = sessionStorage.getItem('accessToken');
async function api(path, options={}) {
  const headers = {'Content-Type':'application/json', ...(options.headers||{})};
  if (accessToken) headers.Authorization=`Bearer ${accessToken}`;
  const res=await fetch(API+path,{...options,headers});
  if(!res.ok) throw new Error((await res.json()).detail || 'Request failed');
  return res.status===204 ? null : res.json();
}
async function register(display_name,email,password){
  const t=await api('/auth/register',{method:'POST',body:JSON.stringify({display_name,email,password,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})});
  accessToken=t.access_token;sessionStorage.setItem('accessToken',accessToken);return t;
}
async function login(email,password){
  const t=await api('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
  accessToken=t.access_token;sessionStorage.setItem('accessToken',accessToken);return t;
}
async function listPeople(search=''){return api('/users?q='+encodeURIComponent(search));}
async function follow(id,on){return api(`/users/${id}/follow`,{method:on?'PUT':'DELETE'});}
async function openChat(userId,onMessage){
  const c=await api(`/chat/direct/${userId}`,{method:'POST'});
  const history=await api(`/chat/${c.id}/messages`);
  const ws=new WebSocket(`${API.replace('http','ws')}/chat/ws/${c.id}?token=${encodeURIComponent(accessToken)}`);
  ws.onmessage=e=>onMessage(JSON.parse(e.data));
  return {conversation:c,history,send:content=>ws.send(JSON.stringify({content})),close:()=>ws.close()};
}
