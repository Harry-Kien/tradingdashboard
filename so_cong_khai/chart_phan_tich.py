"""Mật độ hiển thị phân tích; chỉ thay cách trình bày, không sửa tín hiệu/mức giá."""

HTML = '''<div class="pt-presentation" role="group" aria-label="Trình bày phân tích">
<div class="pt-current" hidden><b class="pt-direction"></b><span class="pt-method"></span><span class="pt-validity"></span><button type="button" class="pt-level-toggle" aria-expanded="false" aria-controls="pt-levels">Mức giá</button></div>
<label class="pt-density">Nhãn phân tích<select id="pt-density" aria-label="Mật độ nhãn phân tích" title="Tinh gọn ưu tiên nến và SL/TP; Chi tiết hiện thêm nhãn bối cảnh."><option value="gon">Tinh gọn</option><option value="du">Chi tiết</option></select></label>
<div id="pt-levels" class="pt-levels" role="region" aria-label="Mức giá của phương án đang xem" hidden></div></div>'''

CSS = '''
.pt-presentation{display:flex;align-items:center;justify-content:flex-end;gap:8px 16px;flex-wrap:wrap;padding:7px 0;color:var(--mute);font-size:12px;min-width:0}
.pt-current{display:flex;align-items:center;gap:8px;flex:1;min-width:140px}.pt-current[hidden]{display:none}
.pt-direction{font-size:11px;letter-spacing:.3px;padding:3px 7px;border:1px solid currentColor;border-radius:5px;white-space:nowrap}
.pt-direction[data-side=MUA]{color:#26a69a}.pt-direction[data-side=BÁN]{color:#ef5350}
.pt-method{color:var(--ink2);font-weight:600;white-space:nowrap;text-overflow:ellipsis;overflow:hidden;min-width:0;max-width:640px}
.pt-validity{white-space:nowrap;font-size:11px;padding:3px 7px;border-radius:20px;background:var(--line);color:var(--ink2)}
.pt-validity[data-state=old],.pt-validity[data-state=reference]{color:var(--warn)}
.pt-density{display:flex;align-items:center;gap:7px;white-space:nowrap;margin:0;font-size:11.5px}
.pt-density select{font:inherit;color:var(--ink2);background:var(--card);border:1px solid var(--line);border-radius:6px;min-height:30px;padding:3px 24px 3px 8px;width:auto}
.pt-current .pt-level-toggle{flex:none;font:inherit;font-size:11px;padding:4px 8px;min-height:28px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink2);cursor:pointer;white-space:nowrap}
.pt-level-toggle[aria-expanded=true]{border-color:var(--series)}.pt-levels{flex-basis:100%;min-width:0;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink2)}.pt-levels[hidden]{display:none}
.pt-level-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,130px),1fr));gap:8px 14px;margin:0}.pt-level-grid>div{min-width:0}.pt-level-grid dt{font-size:11px;color:var(--mute);margin-bottom:3px}.pt-level-grid dd{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;margin:0;overflow-wrap:anywhere}.pt-level-meta{margin:8px 0 0;font-size:11px;line-height:1.6;overflow-wrap:anywhere}.pt-level-warning{color:var(--warn)}
@media(max-width:640px){.pt-presentation{gap:7px;padding:5px 0}.pt-current{flex-basis:100%}.pt-method{flex:1}.pt-validity{max-width:110px;overflow:hidden;text-overflow:ellipsis}.pt-density select{min-height:34px}}
'''

JS = r'''
(()=>{let mode='gon';try{if(localStorage.getItem('so-nhan-phan-tich')==='du')mode='du'}catch(e){}
 const select=document.getElementById('pt-density'),bar=document.querySelector('.pt-current'),panel=document.getElementById('pt-levels'),toggle=bar&&bar.querySelector('.pt-level-toggle');let signature='',expanded=false;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const number=v=>typeof v==='number'&&Number.isFinite(v),fallback=v=>new Intl.NumberFormat(document.documentElement?.lang==='en'?'en-US':'vi-VN',{maximumFractionDigits:8}).format(v);
 function levels(p,format){const price=v=>number(v)?format(v):'—',rows=[[p.loai_vao==='gh'||p.loai_vao==='dung'?'Mức chờ':'Điểm vào',price(p.vao)],['Dừng lỗ',price(p.sl)],...(Array.isArray(p.tp)?p.tp:[]).map((v,i)=>['TP'+(i+1),price(v)+(number(p.rr?.[i])?' · '+new Intl.NumberFormat(document.documentElement?.lang==='en'?'en-US':'vi-VN',{maximumFractionDigits:2}).format(p.rr[i])+'R':'')])];
  const stamp=Date.parse(p.nen),when=Number.isFinite(stamp)?new Date(stamp).toLocaleString(document.documentElement?.lang==='en'?'en-US':'vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'—';
  const reasons=Array.isArray(p.vi_sao_het)?p.vi_sao_het.filter(x=>typeof x==='string').join(' '):'',incomplete=!number(p.vao)||!number(p.sl)||!Array.isArray(p.tp)||!p.tp.length||p.tp.some(v=>!number(v));
  return '<dl class="pt-level-grid">'+rows.map(([k,v])=>'<div><dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd></div>').join('')+'</dl>'
   +'<p class="pt-level-meta">'+esc('Kiểu vào: ')+esc(p.kieu||'—')+' · '+esc('Nến tín hiệu: ')+esc(when)+'</p>'
   +(reasons?'<p class="pt-level-meta pt-level-warning">'+esc(reasons)+'</p>':'')+(incomplete?'<p class="pt-level-meta pt-level-warning">'+esc('Chưa đủ mức giá. Mở phân tích đầy đủ để kiểm tra.')+'</p>':'')}
 const gon=()=>mode!=='du';
 function alpha(color,a){return /^#[0-9a-f]{6}$/i.test(color)?color+Math.round(255*a).toString(16).padStart(2,'0'):color}
 function mien(x,pw){const a=Math.max(0,Math.min(x,pw));return[a,gon()?Math.min(pw,a+Math.max(100,Math.min(320,pw*.34))):pw]}
 function fvg(fs,gia){const inside=fs.filter(z=>z.duoi<=gia&&z.tren>=gia),up=fs.filter(z=>z.duoi>gia).sort((a,b)=>a.duoi-b.duoi),down=fs.filter(z=>z.tren<gia).sort((a,b)=>b.tren-a.tren);
  return gon()?[...inside.slice(-1),...up.slice(0,1),...down.slice(0,1)]:[...inside,...up.slice(0,2),...down.slice(0,2)]}
 function paint(p,hidden,available=true,format=fallback){if(select)select.disabled=!available;if(!bar)return;bar.hidden=!p||hidden;if(bar.hidden){signature='';expanded=false;if(panel){panel.hidden=true;panel.textContent=''}if(toggle)toggle.setAttribute('aria-expanded','false');return}
  const status=p.nhan_gia||(p.cu?'Đã quá hạn':p.hieu_luc===false?'Chỉ tham khảo':p.hieu_luc?'Còn hiệu lực':'Chưa xác định hiệu lực'),sig=JSON.stringify([p.ma,p.huong,p.ten,status,p.vao,p.sl,p.tp,p.rr,p.kieu,p.nen,p.vi_sao_het,p.loai_vao]);if(panel)panel.hidden=!expanded;if(sig===signature)return;signature=sig;if(panel)panel.innerHTML=levels(p,format);
  const side=bar.querySelector('.pt-direction'),method=bar.querySelector('.pt-method'),state=bar.querySelector('.pt-validity');side.textContent=p.huong||'—';side.dataset.side=p.huong||'';method.textContent=p.ten||'Phương án đang xem';method.title=p.ten||'';state.textContent=state.title=status;state.dataset.state=p.cu?'old':p.hieu_luc===false?'reference':'current'}
 if(toggle)toggle.addEventListener('click',()=>{if(bar.hidden||!panel)return;expanded=!expanded;panel.hidden=!expanded;toggle.setAttribute('aria-expanded',String(expanded))});
 window.PTUI={gon,alpha,mien,fvg,paint,onChange:null};if(select){select.value=mode;select.addEventListener('change',()=>{mode=select.value==='du'?'du':'gon';try{localStorage.setItem('so-nhan-phan-tich',mode)}catch(e){}if(PTUI.onChange)PTUI.onChange()})}
})();
'''
