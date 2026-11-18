export const byId=id=>document.getElementById(id);
export const count=v=>v.toLocaleString('en-US');
export const number=v=>v==null?'Missing':Number(v.toPrecision(5)).toString();
export function choices(select,values,label,name=v=>v){
  select.replaceChildren(new Option(label,''),...values.map(v=>new Option(name(v),String(v))));
}
export async function get(path,options={}){
  const res=await fetch(path,options);const data=await res.json();
  if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'The requested data could not be loaded.');
  return data;
}
export function error(e){const box=byId('error');box.textContent=e.message||'Could not load this page.';box.hidden=false;}
export function toolStatus(el,model){el.className='badge status';el.textContent=model.status==='MODEL_NOT_LOADED'?'NOT LOADED':model.status;}
