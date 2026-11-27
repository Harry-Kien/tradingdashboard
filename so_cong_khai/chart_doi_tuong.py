"""Danh sách hình vẽ: dùng chung dữ liệu, quyền sửa, hoàn tác và đồng bộ chart hiện có."""
from .hinh_ve import TOI_DA_BYTE, TOI_DA_HINH

CSS = r"""
.cdo{width:min(850px,calc(100vw - 24px));height:min(680px,85dvh);max-height:85dvh;box-sizing:border-box;padding:18px;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--ink);box-shadow:0 18px 70px #0008}.cdo[open]{display:grid;grid-template-rows:auto auto minmax(0,1fr) auto}
.cdo::backdrop{background:#0007}.cdo header{display:flex;align-items:center;justify-content:space-between;gap:12px}.cdo h2{font-size:18px;margin:0}.cdo small,.cdo-note{color:var(--ink2);font-size:12px}.cdo-search{width:100%;box-sizing:border-box;margin:14px 0 8px;min-height:38px;padding:8px 10px;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:7px;font:inherit;font-size:13px}.cdo-list{min-height:0;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable}
.cdo-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:12px 4px;border-bottom:1px solid var(--line)}.cdo-row[data-selected=true]{background:color-mix(in srgb,var(--series) 8%,transparent)}.cdo-row strong,.cdo-row small{display:block;overflow-wrap:anywhere}.cdo-row strong{font-size:13px}.cdo-row small{margin-top:4px}.cdo-actions{display:flex;flex-wrap:wrap;gap:5px}.cdo button{min-height:32px;padding:4px 9px;background:var(--card);color:var(--ink2);border:1px solid var(--line);border-radius:6px;font:inherit;font-size:12px;cursor:pointer}.cdo button:hover:not(:disabled){background:var(--bg);color:var(--ink)}.cdo button:focus-visible,.cdo-search:focus-visible{outline:2px solid var(--series);outline-offset:2px}.cdo button:disabled{opacity:.4;cursor:default}.cdo button[aria-pressed=true]{border-color:var(--series);color:var(--series)}.cdo [data-act=delete]{color:var(--loss)}.cdo-bottom{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding-top:12px}.cdo-bottom [role=status]{flex:1 0 100%;font-size:12px;min-height:18px;color:var(--ink2)}.cdo-empty{padding:24px 8px;text-align:center;color:var(--ink2)}.cdo [hidden]{display:none!important}
@media(max-width:640px){.cdo{padding:12px}.cdo-row{grid-template-columns:1fr}.cdo-actions button{min-height:38px}}
"""

CORE_JS = r"""
window.CHART_OBJECTS=(()=>{
 const fold=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
 const list=(g,q='')=>{const query=fold(q).trim();return(g?.VE?.ds||[]).slice().reverse().filter(h=>!query||fold([(g.VEC[h.k]||[h.k])[0],h.chu,h.id].join(' ')).includes(query))};
 function act(g,action,id){if(!['select','hide','lock','duplicate','delete','front','back'].includes(action))return'unknown';
  if(!g?.D||!g.VE||g.VE.tam||g.VE.keo||window.PHAT_LAI)return'busy';const V=g.VE,i=V.ds.findIndex(h=>h.id===id),h=V.ds[i];if(!h)return'missing';
  if(action==='select'){if(h.an||V.an)return'hidden';g.veCong('tro');V.chon=id;g.veTb();g.lwPhu();return'ok'}
  if(!g.veDuoc||!g.veDuoc())return'denied';if(action==='delete'&&h.khoa)return'locked';
  if(action==='duplicate'){if(V.ds.length>=__MAX_HINH__)return'limit';const n=JSON.parse(JSON.stringify(h));let next=null;
   for(let k=0;k<8;k++){const candidate=g.moiId();if(!V.ds.some(x=>x.id===candidate)){next=candidate;break}}if(!next)return'limit';n.id=next;delete n.khoa;
   if(new TextEncoder().encode(JSON.stringify([...V.ds,n])).length>__MAX_BYTE__)return'limit';V.ds.push(n);V.chon=n.id}
  else if(action==='hide'){if(h.an)delete h.an;else{h.an=1;if(V.chon===id)V.chon=null}}
  else if(action==='lock'){if(h.khoa)delete h.khoa;else h.khoa=1}
  else if(action==='delete'){V.ds.splice(i,1);if(V.chon===id)V.chon=null}
  else{V.ds.splice(i,1);if(action==='front')V.ds.push(h);else V.ds.unshift(h)}
  g.veLuu();g.veTb();g.lwPhu();return'ok'}
 return{list,act};
})();
""".replace('__MAX_HINH__', str(TOI_DA_HINH)).replace('__MAX_BYTE__', str(TOI_DA_BYTE))

JS = CORE_JS + r"""
(()=>{const G=window.BDMN,core=window.CHART_OBJECTS,bar=document.querySelector('.tools.t2');if(!G||!bar||document.documentElement.classList.contains('anh'))return;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const button=document.createElement('button');button.type='button';button.className='ghost';button.textContent='Hình vẽ';button.title='Danh sách hình vẽ (Alt+O)';bar.appendChild(button);
 let dialog=null,scope='',shown=50;
 const key=g=>g&&g.D?(g.veKhoa?g.veKhoa():g.ma)+'|'+g.tf+'|'+(g.D._chart_epoch??''):null;
 const current=()=>{const g=G();return g&&key(g)===scope?g:null};
 function close(){if(dialog)dialog.close()}
 function paint(){if(!dialog?.open)return;const g=current();if(!g){close();return}const active=document.activeElement,keep=active?.dataset?.act?{act:active.dataset.act,id:active.dataset.id}:null;
  const q=dialog.querySelector('input').value,ds=core.list(g,q),total=g.VE.ds.length;
  dialog.querySelector('[data-count]').textContent=ds.length+' / '+total;const action=(h,a,text,pressed,disabled)=>`<button type="button" data-act="${a}" data-id="${esc(h.id)}"${pressed!=null?` aria-pressed="${pressed}"`:''}${disabled?' disabled':''}>${text}</button>`;
  dialog.querySelector('.cdo-list').innerHTML=ds.length?ds.slice(0,shown).map(h=>`<div class="cdo-row" data-selected="${g.VE.chon===h.id}"><div><strong>${esc((g.VEC[h.k]||[h.k])[0])}</strong><small>${esc(h.chu||h.id)}</small></div><div class="cdo-actions">`
   +action(h,'select','Chọn',null,!!h.an||!!g.VE.an)+action(h,'hide',h.an?'Hiện':'Ẩn',!!h.an)+action(h,'lock',h.khoa?'Mở khóa':'Khóa',!!h.khoa)+action(h,'duplicate','Nhân bản')+action(h,'front','Lên trên')+action(h,'back','Xuống dưới')+action(h,'delete','Xóa',null,!!h.khoa)+'</div></div>').join(''):`<p class="cdo-empty">${total?'Không tìm thấy hình vẽ.':'Chưa có hình vẽ cho mã này.'}</p>`;
  dialog.querySelector('[data-more]').hidden=ds.length<=shown;dialog.querySelector('[data-show]').hidden=!g.VE.an;
  dialog.querySelector('[data-undo]').disabled=!g.VE.cu.length;dialog.querySelector('[data-redo]').disabled=!g.VE.lai.length;
  if(keep){const b=[...dialog.querySelectorAll('[data-act]')].find(b=>b.dataset.act===keep.act&&b.dataset.id===keep.id);(b&&!b.disabled?b:dialog.querySelector('input')).focus()}}
 const message=code=>({'busy':'Hãy hoàn tất thao tác vẽ hoặc dừng phát lại trước.','missing':'Hình vẽ đã thay đổi. Danh sách đã được cập nhật.','denied':'Cần đăng nhập và đồng bộ chart trước khi chỉnh sửa.','locked':'Mở khóa hình trước khi xóa.','hidden':'Hiện hình vẽ trước khi chọn.','limit':'Đã đạt giới hạn lưu bản vẽ.'}[code]||'');
 function open(){if(dialog){dialog.querySelector('input').focus();return}const g=G();if(!g?.D){button.title='Đang tải chart, hãy thử lại sau.';return}scope=key(g);shown=50;
  const d=document.createElement('dialog');dialog=d;d.className='cdo';d.setAttribute('aria-label','Danh sách hình vẽ');d.innerHTML='<header><div><h2>Hình vẽ</h2><small data-count></small></div><button type="button" data-close>Đóng</button></header><input class="cdo-search" type="search" placeholder="Tìm hình vẽ…" aria-label="Tìm hình vẽ"><div class="cdo-list"></div><div class="cdo-bottom"><button type="button" data-undo>Hoàn tác</button><button type="button" data-redo>Làm lại</button><button type="button" data-show hidden>Hiện tất cả hình vẽ</button><button type="button" data-more hidden>Hiện thêm</button><span role="status" aria-live="polite"></span></div>';
  (document.fullscreenElement||document.body).appendChild(d);d.addEventListener('close',()=>{d.remove();if(dialog===d)dialog=null;button.focus()});
  d.addEventListener('input',()=>{shown=50;paint()});
  d.addEventListener('keydown',e=>{e.stopPropagation();if(e.target.matches('input,textarea,[contenteditable=true]'))return;if((e.ctrlKey||e.metaKey)&&/^[zy]$/i.test(e.key)){e.preventDefault();const g=current();if(!g)return;const redo=e.key.toLowerCase()==='y'||e.shiftKey;(redo?g.veLam:g.veHoan)();paint()}});
  d.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.hasAttribute('data-close')){close();return}const g=current();if(!g){close();return}
   if(b.hasAttribute('data-more'))shown+=50;else if(b.hasAttribute('data-undo'))g.veHoan();else if(b.hasAttribute('data-redo'))g.veLam();else if(b.hasAttribute('data-show')){g.VE.an=false;g.veTb();g.lwPhu()}
   else if(b.dataset.act){const result=core.act(g,b.dataset.act,b.dataset.id);d.querySelector('[role=status]').textContent=message(result);if(result==='ok'&&b.dataset.act==='select'){close();return}}
   paint()});d.showModal();paint();d.querySelector('input').focus()}
 button.addEventListener('click',open);addEventListener('chart-context-changing',close);
 addEventListener('keydown',e=>{if(!e.altKey||e.ctrlKey||e.metaKey||e.key.toLowerCase()!=='o'||e.target.closest('input,textarea,select,[contenteditable=true]')||document.querySelector('dialog[open]'))return;e.preventDefault();open()});
 setInterval(()=>{if(dialog?.open&&document.visibilityState==='visible'){const g=current();if(!g)close()}},500);
})();
"""
