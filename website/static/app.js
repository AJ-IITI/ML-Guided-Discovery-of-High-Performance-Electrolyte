import {byId as $,count,get,error,toolStatus} from './ui.js';
import {trend} from './charts.js';
import {explore} from './explore.js';
import {predict} from './predict.js';
async function init(){
  const page=document.body.dataset.page;
  if(page==='models'){
    const {models}=await get('/api/models/status');
    document.querySelectorAll('[data-status]').forEach(el=>toolStatus(el,models[el.dataset.status]));return;
  }
  const s=await get('/api/dataset/summary');
  if(page==='explore')return explore(s);
  if(page==='predict')return predict(s);
  $('stat-rows').textContent=count(s.rows);$('stat-labelled').textContent=count(s.labelled);
  $('stat-solvents').textContent=s.choices.solvent.length;$('stat-salts').textContent=s.salt_pairs;
  const f=await get('/api/dataset/figures'),target=$('home-chart');let width=0;
  trend(target,f.trend,true);new ResizeObserver(entries=>{const w=Math.round(entries[0].contentRect.width);if(w!==width){width=w;trend(target,f.trend,true);}}).observe(target);
}
init().catch(error);
