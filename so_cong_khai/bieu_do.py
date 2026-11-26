"""Trang biểu đồ vàng kiểu MT5: nến, chỉ báo và luật của chủ dự án, lệnh đang mở, cảnh báo, tính khối lượng, hỏi AI.
Dữ liệu lấy từ /api/gia, /api/song (luồng tick), /api/canh-bao, /api/ai. Trang không có lời gọi đặt lệnh nào."""
from __future__ import annotations

from html import escape

from . import trang

CSS = """
.desk{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:16px;align-items:start;margin-top:14px}
@media(max-width:980px){.desk{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.col{display:grid;gap:16px;align-content:start}
.grow{flex:1}.act:disabled{cursor:progress;opacity:.75}
#gon-btn{display:none;gap:6px;font-weight:600}.chartp.max #gon-btn{display:inline-flex;align-items:center}#gon-btn .gm{font-size:12px;line-height:1}
.chartp.max.gon .tools.t2,.chartp.max.gon #bot-tt,.chartp.max.gon #dv{display:none!important}
.chartp.max.gon{padding:6px 8px}.chartp.max.gon .tools{margin-bottom:6px}
@media(max-width:640px){.chartp.max #gon-btn{width:40px;padding:0;justify-content:center}#gon-btn .gt{display:none}
.chartp.max.gon .tools .sel,.chartp.max.gon .tools .seg.zo,.chartp.max.gon .tools #pt-btn{display:none}
.chartp.max.gon .tools .seg.tf{order:0;flex:1 1 0;min-width:0}.chartp.max.gon #gon-btn,.chartp.max.gon #fs-btn{order:1}}
.chartp{position:relative}.chartp.max{position:fixed;inset:0;z-index:30;display:flex;flex-direction:column;padding:10px 12px;border-radius:0;border:0;background:var(--card);overflow:auto}
html.khoa{overflow:hidden}.chartp.max .stage{flex:1 1 0;min-height:320px}.chartp.max #dv{flex:none;max-height:min(30vh,280px);overflow:auto}.chartp.max .hint{display:none}
main{max-width:1520px}.bar>div{max-width:1520px}
aside.pt{font-size:13px;border-left:3px solid var(--series)}aside.pt[hidden]{display:none!important}
.stage aside.pt{flex:none;width:372px;contain:size;overflow:auto;border:0;border-left:1px solid var(--line);border-radius:0;box-shadow:none}
.chartp.max .stage{display:flex}.chartp.max #cv{flex:1 1 0;min-width:0;width:0;height:auto}
@media(max-width:760px){.stage aside.pt{position:absolute;left:0;right:0;bottom:0;width:auto;max-height:48%;contain:none;border-left:0;border-top:1px solid var(--line)}
.chartp.max .stage{display:block}.chartp.max #cv{width:100%;height:100%}}
.pt h3{margin:14px 0 6px}.pt h3:first-of-type{margin-top:0}.pt .x{position:sticky;top:0;float:right;border:1px solid var(--line);background:var(--card);border-radius:6px;padding:3px 8px;cursor:pointer;color:var(--ink2);font-weight:700}
.pa{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0}.pa.sel{border-color:var(--series);box-shadow:inset 3px 0 0 var(--series)}
.pa .hd{display:flex;justify-content:space-between;gap:8px;align-items:baseline}.pa .hd b{font-size:13.5px}.pa .hd small{color:var(--mute)}
.ph{border-top:1px dashed var(--line);margin:10px 0 0;padding:8px 0 0}.ph .hl.xau{color:var(--loss)}.phdk{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12.5px;margin:6px 0}.phdk .dat{color:var(--gain)}.phdk .hong{color:var(--loss)}.phb{display:grid;grid-template-columns:minmax(0,1.7fr) repeat(6,minmax(0,1fr));gap:2px 6px;font-size:11.5px;font-variant-numeric:tabular-nums;margin:6px 0;contain:inline-size;overflow-x:auto}.phb>*{min-width:0;overflow-wrap:anywhere}.ph .hd{flex-wrap:wrap}.ph .hd small{min-width:0}.phb b{font-weight:600;color:var(--mute)}.vph{margin-top:6px}.phn{margin:10px 0 2px;padding-top:10px;border-top:1px dashed var(--line)}.phnt{font-size:13px}.phnc{display:block;color:var(--mute);font-size:11.5px;margin:1px 0 6px}.phr{border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin:6px 0;background:var(--card)}.phr.song{border-color:color-mix(in srgb,var(--series) 55%,var(--line))}.phh{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}.phh b{font-size:13px}.phr>small{display:block;color:var(--mute);font-size:12px;margin:2px 0 4px}.phg{display:flex;flex-wrap:wrap;align-items:center;gap:4px 14px;font-size:12.5px;font-variant-numeric:tabular-nums}.phg .vph{margin:0 0 0 auto}.pa .dir{margin:6px 0 4px}.pa .lv{display:grid;grid-template-columns:auto 1fr auto;gap:2px 10px;font-variant-numeric:tabular-nums;margin:6px 0}
.pa .lv span{color:var(--ink2)}.pa .lv b{text-align:right}.pa .lv i{font-style:normal;color:var(--mute);text-align:right;font-size:12px}
.pa .ve,.pa .kcb{font-weight:600;font-size:12px;color:var(--series);background:none;border:1px solid var(--series);border-radius:6px;padding:4px 9px;cursor:pointer;margin-top:4px}
.pa .ve,.pa .kcb{display:inline-flex;align-items:center;min-height:28px;transition:background-color .12s,color .12s}.pa .ve:hover,.pa .kcb:hover{background:color-mix(in srgb,var(--series) 9%,transparent)}.pa .ve[aria-pressed=true],.pa .kcb[aria-pressed=true]{background:var(--series);color:var(--btn-ink)}.pa .ve:focus-visible,.pa .kcb:focus-visible,.pt .x:focus-visible{outline:2px solid var(--series);outline-offset:2px}.pt .x{display:inline-flex;align-items:center;gap:5px;font-size:12px}.pt .x:hover{border-color:var(--mute);color:var(--ink)}
.kc{margin-top:10px;padding-top:10px;border-top:1px dashed var(--line)}.kc>b{display:block;font-size:12.5px}.kc>small{color:var(--mute);font-size:12px}.kc .kv{padding:4px 0;font-size:12.5px}.kcl{display:grid;grid-template-columns:auto 1fr auto auto;gap:2px 8px;font-size:12px;font-variant-numeric:tabular-nums;margin:8px 0;color:var(--ink2)}.kcl b{text-align:right}.hl{display:inline-block;font-size:11.5px;font-weight:700;border:1px solid var(--line);border-radius:4px;padding:2px 7px;color:var(--ink2);vertical-align:middle}.hl.ok{color:var(--gain);border-color:var(--gain)}.ppc{margin:2px 0 8px}.ictk{display:grid;grid-template-columns:18px 1fr;gap:7px 8px;font-size:12.5px;line-height:1.45;color:var(--ink2);margin:8px 0}.ictk i{font-style:normal;font-weight:700;text-align:center}.ictk i.dat{color:var(--gain)}.ictk i.chua{color:var(--loss)}.ictk i.kx{color:var(--mute)}.ictk b{color:var(--ink)}.ictb{display:inline-flex;align-items:center;min-height:28px;font-weight:600;font-size:12px;color:var(--series);background:none;border:1px solid var(--series);border-radius:6px;padding:4px 9px;cursor:pointer;margin-top:4px;transition:background-color .12s,color .12s}.ictb:hover{background:color-mix(in srgb,var(--series) 9%,transparent)}.ictb[aria-pressed=true]{background:var(--series);color:var(--btn-ink)}.ictb:focus-visible{outline:2px solid var(--series);outline-offset:2px}.tn{font-size:12.5px;color:var(--ink2);border:1px solid var(--gain);border-left:3px solid var(--gain);border-radius:6px;padding:8px 10px;margin:0 0 8px}.tn b{color:var(--ink)}.hl.xau{color:var(--loss);border-color:var(--loss)}.hocr{display:grid;gap:2px;padding:8px 0;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--ink2)}.hocr:last-of-type{border-bottom:0}.hocr b{color:var(--ink)}.hocr i{font-style:normal;font-weight:700}.hocr .hl{justify-self:start;margin-top:2px}details.kc{margin-top:10px}.kc summary{text-transform:none;letter-spacing:0;font-size:12.5px;font-weight:400;color:var(--ink2);padding:0;line-height:1.5}.kc summary b{color:var(--ink);font-weight:700}.kc[open] summary{margin-bottom:4px}.kc>small{display:block}@media(min-width:981px){.col>aside.pt{max-height:calc(100vh - 92px);overflow:auto}}
.tools{display:flex;gap:8px 12px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--card);box-shadow:0 1px 0 rgba(16,24,40,.04)}
.seg button{display:inline-flex;align-items:center;justify-content:center;min-height:30px;font-weight:600;font-size:12px;color:var(--ink2);background:none;border:0;border-right:1px solid var(--line);
padding:0 11px;cursor:pointer;transition:background-color .12s,color .12s}
.seg button:last-child{border-right:0}.seg button:hover:not([aria-pressed=true]):not(:disabled){background:var(--bg);color:var(--ink)}
.seg button[aria-pressed=true]{background:var(--series);color:var(--btn-ink)}.seg button:disabled{color:var(--mute);opacity:.5;cursor:default}
.seg.zo button{width:32px;padding:0}#z-out{--i:var(--i-tru)}#z-in{--i:var(--i-cong)}#z-now{--i:var(--i-hien-tai)}
.chips{display:flex;gap:5px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:6px;min-height:28px;padding:0 9px 0 7px;border-radius:999px;font-weight:600;font-size:12px;cursor:pointer;
color:var(--ink);background:var(--card);border:1px solid var(--line);transition:background-color .12s,border-color .12s,color .12s}
.chip i{width:10px;height:10px;border-radius:50%;flex:none;box-sizing:border-box;background:var(--c,var(--series));border:2px solid var(--c,var(--series))}
.chip[aria-pressed=true]{background:color-mix(in srgb,var(--c,var(--series)) 9%,var(--card));border-color:color-mix(in srgb,var(--c,var(--series)) 42%,var(--line))}
.chip[aria-pressed=false]{color:var(--ink2)}.chip[aria-pressed=false] i{background:none;border-color:var(--mute)}
.chip:hover{border-color:var(--mute)}.chip:active{transform:translateY(1px)}
.chip:focus-visible,.seg button:focus-visible,.fld input:focus-visible{outline:2px solid var(--series);outline-offset:1px}
@media(pointer:coarse){.chip,.seg button{min-height:34px}}
.sel select{min-height:32px;font-weight:700;font-size:12.5px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;padding:0 8px;cursor:pointer;max-width:220px;box-shadow:0 1px 0 rgba(16,24,40,.04)}.sel select:hover{border-color:var(--mute)}.sel select:focus-visible{outline:2px solid var(--series);outline-offset:2px}
.tuy{position:relative;margin:0}.tuy summary{list-style:none;padding:0 10px}.tuy summary::-webkit-details-marker{display:none}.tuy summary b{color:var(--mute);font-weight:600;margin-left:2px}.tuy[open] summary{border-color:var(--series)}.chips.pop{position:absolute;z-index:6;top:calc(100% + 6px);left:0;width:max-content;max-width:min(420px,calc(100vw - 24px));background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;box-shadow:0 10px 30px rgba(16,24,40,.16)}
.bott{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font-size:12.5px;color:var(--ink2);margin:0 0 10px;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg)}.bott:empty{display:none}.bott b{color:var(--ink)}.bott .mo{color:var(--mute);font-size:12px}
body[data-khac] #rk,body[data-khac] #ai{display:none}
.stage[data-tai]::after{content:"Đang tải dữ liệu nến…";position:absolute;inset:0;display:grid;place-items:center;color:var(--mute);font-size:13px;background:var(--card)}
.stage{position:relative;border:1px solid var(--line);border-radius:6px;overflow:hidden}
#cv{width:100%;height:clamp(420px,calc(100vh - 395px),760px);display:block;cursor:crosshair;touch-action:none}
#lw{display:none;width:100%;height:clamp(420px,calc(100vh - 395px),760px)}#lwo{display:none;position:absolute;left:0;top:0;pointer-events:none;z-index:2}
body[data-lw] #lw,body[data-lw] #lwo{display:block}body[data-lw] #cv{display:none}#read{z-index:3}.stage[data-tai]::after{z-index:4}
@media(max-width:640px){#lw{height:440px}}.chartp.max #lw{flex:1 1 0;min-width:0;width:0;height:auto}
@media(max-width:760px){.chartp.max #lw{width:100%;height:100%}}.hint a{color:var(--ink2)}
@media(max-width:640px){#cv{height:440px}}
#read{position:absolute;left:6px;top:4px;font-size:12px;line-height:1.5;pointer-events:none;padding:1px 5px;border-radius:4px;font-variant-numeric:tabular-nums}
.hint{font-size:12px;color:var(--mute);margin:8px 0 0}
.side h3{margin:16px 0 6px}.side h3:first-child{margin-top:2px}
.kv{display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:5px 0;border-bottom:1px solid var(--line);color:var(--ink2)}
.kv:last-child{border-bottom:0}.kv b{color:var(--ink);font-variant-numeric:tabular-nums;text-align:right}
.dir{display:inline-block;min-width:74px;text-align:center;font-weight:700;font-size:11.5px;border-radius:4px;padding:3px 7px;border:1px solid var(--line);color:var(--ink)}
.dir.up{border-color:var(--gain);color:var(--gain)}.dir.dn{border-color:var(--loss);color:var(--loss)}
.verdict{font-weight:700;font-size:15px;line-height:1.35;margin:2px 0 6px}.why{font-size:12.5px;color:var(--mute);margin:0 0 6px}
.stale{background:var(--warnbg);color:var(--warn);border:1px solid var(--warnline);border-radius:8px;padding:8px 12px;font-size:13px;margin:0 0 10px}
.go{width:100%;min-height:38px;font-size:13px;margin:8px 0 4px}.go:disabled{background:var(--track);border-color:var(--line);color:var(--mute);cursor:not-allowed;box-shadow:none}
.live{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--gain);margin-right:6px;vertical-align:1px}.live.off{background:var(--mute)}
.fld{display:grid;grid-template-columns:1fr 112px;gap:8px;align-items:center;font-size:13px;color:var(--ink2);padding:4px 0}
.fld input{font-weight:600;font-size:13.5px;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);text-align:right;width:100%;font-variant-numeric:tabular-nums}
#rko{margin-top:10px}
/* cột phải (25/11/2026): dải tài khoản cố định, thẻ chuyển, cảnh báo gọn */
.col{grid-template-columns:minmax(0,1fr)}.col>*{min-width:0}
.tkt{position:sticky;top:64px;z-index:6;padding:10px 12px;display:grid;gap:8px}@media(max-width:980px){.tkt{position:static}}
.tkt .th{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:12.5px;color:var(--mute)}.tkt .th b{color:var(--ink);font-size:13px}
.tkt .tg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.tkt .tg div{display:grid;gap:1px;min-width:0;border:1px solid var(--line);border-radius:8px;padding:5px 8px}
.tkt .tg small{font-size:11px;color:var(--mute)}.tkt .tg b{font-size:14px;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rrb{display:grid;gap:4px;font-size:12px;color:var(--ink2)}.rrb .tr{height:7px;border-radius:99px;background:var(--track);overflow:hidden}.rrb .tr i{display:block;height:100%;border-radius:99px;background:var(--gain)}
.rrb.vua .tr i{background:var(--warn)}.rrb.cao .tr i{background:var(--loss)}.rrb.cao b{color:var(--loss)}.rrb.vua b{color:var(--warn)}
.tkt .ln{display:flex;align-items:center;gap:6px;font-size:12px;font-variant-numeric:tabular-nums;color:var(--ink2);min-width:0}.tkt .ln em{margin-left:auto;font-style:normal;white-space:nowrap}
.tkt .ph{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:11.5px;color:var(--mute);border-top:1px dashed var(--line);padding-top:6px}.tkt .ph b{color:var(--ink2);font-weight:600}
.ctab{display:flex;gap:4px;padding:4px;border:1px solid var(--line);border-radius:10px;background:var(--card)}
.ctab button{flex:1;min-width:0;border:0;background:none;color:var(--ink2);font:inherit;font-size:12.5px;font-weight:600;padding:7px 4px;border-radius:7px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:5px}
.ctab button[aria-selected=true]{background:color-mix(in srgb,var(--series) 16%,transparent);color:var(--ink)}.ctab button:focus-visible{outline:2px solid var(--series);outline-offset:1px}
.ctab b{min-width:17px;height:17px;padding:0 4px;border-radius:99px;background:var(--loss);color:#fff;font-size:10.5px;line-height:17px}
.col[data-tab=cb] .tabp:not([data-t=cb]),.col[data-tab=tk] .tabp:not([data-t=tk]),.col[data-tab=nk] .tabp:not([data-t=nk]),.col[data-tab=rk] .tabp:not([data-t=rk]){display:none}
.cbl{display:flex;flex-wrap:wrap;gap:4px;margin:2px 0 6px}.cbl button{border:1px solid var(--line);background:none;color:var(--ink2);font:inherit;font-size:11.5px;padding:3px 9px;border-radius:99px;cursor:pointer}
.cbl button[aria-pressed=true]{border-color:var(--series);color:var(--ink)}
.al2{border-bottom:1px solid var(--line)}.al2:last-of-type{border-bottom:0}.al2 summary{display:flex;align-items:center;gap:6px;padding:7px 0;cursor:pointer;list-style:none;font-size:12.5px;min-width:0}
.al2 summary::-webkit-details-marker{display:none}.al2 .tag{flex:none;font-size:10.5px;font-weight:700;letter-spacing:.02em;padding:2px 6px;border-radius:5px;background:var(--card2);color:var(--ink2);border:1px solid var(--line)}
.al2 summary{flex-wrap:wrap;row-gap:3px}.al2 .nd{order:9;flex:1 1 100%;min-width:0;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;color:var(--ink2);line-height:1.4}
.al2 time{flex:none;margin-left:auto;color:var(--mute);font-size:11.5px;font-variant-numeric:tabular-nums}.al2[open] .nd{display:none}
.al2 em{flex:none;font-style:normal;font-size:11px;color:var(--mute)}.al2 p{margin:0 0 8px;font-size:12.5px;color:var(--ink2)}.al2.new summary{box-shadow:inset 3px 0 0 var(--series);padding-left:7px}
.al{padding:8px 0;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink2)}.al:last-of-type{border-bottom:0}
.al b{display:block;color:var(--ink);font-size:13.5px}.al span{display:block;margin:2px 0}.al small{color:var(--mute);font-size:12px}
.al.new b::before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--series);margin-right:6px;vertical-align:1px}
.toasts{position:fixed;right:16px;bottom:16px;display:grid;gap:10px;z-index:40;max-width:340px}
.toast{background:var(--ink);color:var(--card);border-radius:10px;padding:12px 14px;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.22);cursor:pointer}
.toast b{display:block;font-size:14px;margin-bottom:3px}
.blw{overflow-x:auto;margin:6px 0}.blt{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}.blt th{color:var(--mute);font-weight:600;text-align:left;padding:4px 6px;border-bottom:1px solid var(--line);white-space:nowrap}.blt td{padding:5px 6px;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:top}.blt td small{display:block;color:var(--mute);font-size:11px;font-weight:400}.blt tr.hl1 td:first-child{box-shadow:inset 3px 0 0 var(--series)}.blt tr.chon td{background:color-mix(in srgb,var(--series) 12%,transparent)}.blt td.mo{color:var(--mute);white-space:normal;min-width:140px}.blt td:first-child{white-space:normal;min-width:110px;max-width:160px}.blt td:first-child b{font-weight:600}.blt .ve{padding:3px 10px;min-height:28px;margin:4px 0 0}details.bl>summary{cursor:pointer;margin:10px 0 4px}.bxh small.ci{display:block;font-size:11px}.kys{vertical-align:middle;margin-left:4px}html.anh .chartp>*:not(.stage),html.anh .vetb,html.anh .toasts,html.anh #pt,html.anh .stage>#pt{display:none!important}html.anh .chartp.max{padding:0}.anh-dau{position:absolute;left:46%;top:50%;transform:translate(-50%,-50%);z-index:5;font:700 44px Tahoma,"Segoe UI",sans-serif;opacity:.09;pointer-events:none;color:var(--ink);letter-spacing:1px;white-space:nowrap}.bxh small.ci i{white-space:nowrap}.bxh.dsr{grid-template-columns:1fr auto auto auto auto}.bxh{display:grid;grid-template-columns:1fr auto auto auto;gap:5px 10px;font-size:12px;font-variant-numeric:tabular-nums;color:var(--ink2);margin:8px 0}.bxh b{color:var(--mute);font-weight:600}.bxh i{font-style:normal;font-weight:700}.ppt .kl{margin-left:auto}@media(max-width:640px){.ppt .kl{margin-left:6px;flex:none}}
.btc{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;font-size:12px;color:var(--mute)}.btc b{font-weight:600;color:var(--ink2);border:1px solid var(--line);border-radius:999px;padding:2px 9px;font-variant-numeric:tabular-nums}.btc b.duong{color:var(--gain);border-color:var(--gain)}.btb{display:grid;grid-template-columns:repeat(4,auto);justify-content:start;gap:3px 18px;font-size:12px;font-variant-numeric:tabular-nums;margin:6px 0;color:var(--ink2)}.btb b{color:var(--mute);font-weight:600}
.plct{font-size:12.5px;color:var(--ink2)}.plct>summary{display:inline-flex;align-items:center;gap:6px;list-style:none;cursor:pointer;color:var(--series);font-weight:600;font-size:12.5px;text-transform:none;letter-spacing:0;padding:2px 0}.plct>summary::-webkit-details-marker{display:none}.plct>summary::before{content:"▸";display:inline-block;transition:transform .15s}.plct[open]>summary::before{transform:rotate(90deg)}.plct>summary:focus-visible{outline:2px solid var(--series);outline-offset:2px}.plct .why{margin:6px 0 0}details.hint{margin:8px 0 0}#nk a,#cb a{color:var(--series)}
.nkd{display:grid;grid-template-columns:auto 1fr auto;gap:2px 8px;align-items:center;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);padding:7px 2px;font:inherit;font-size:12.5px;color:var(--ink2);cursor:pointer;font-variant-numeric:tabular-nums;transition:background-color .12s}.nkd:hover{background:var(--bg)}.nkd.sel{box-shadow:inset 3px 0 0 var(--series);background:color-mix(in srgb,var(--series) 7%,transparent)}.nkd:focus-visible{outline:2px solid var(--series);outline-offset:-2px}.nkd b{color:var(--ink);font-size:13px}.nkd em{font-style:normal;font-weight:700;font-size:12px}.nkd small{grid-column:1/-1;color:var(--mute);font-size:12px}.nkd i{width:8px;height:8px;border-radius:50%;background:var(--line)}.nkd i.song{background:var(--gain);animation:nhip 1.8s ease-out infinite}.nkd i.ok{background:var(--gain)}.nkd i.xau{background:var(--loss)}@media(prefers-reduced-motion:reduce){.nkd i.song{animation:none}}
.tkl{display:grid;grid-template-columns:auto 1fr auto;gap:2px 8px;align-items:center;padding:7px 0;border-bottom:1px solid var(--line);font-size:12.5px;font-variant-numeric:tabular-nums}.tkl:last-of-type{border-bottom:0}.tkl b{font-size:13px}.tkl small{grid-column:1/-1;color:var(--mute);font-size:12px}.tkl .gain,.tkl .loss{font-weight:700}#tk a{color:var(--series)}
.tip{position:absolute;z-index:5;pointer-events:none;max-width:310px;background:var(--card);color:var(--ink2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;line-height:1.45;box-shadow:0 8px 24px rgba(16,24,40,.18)}.tip[hidden]{display:none}.tip b{display:block;color:var(--ink);font-size:12.5px;margin-bottom:2px}.tip span{display:block;margin-top:3px}
.dvb{display:grid;gap:8px;border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:10px 0 0;background:var(--card)}.dvb[hidden]{display:none}
.ppt{display:flex;gap:4px;flex-wrap:wrap}.ppx{display:inline-flex;align-items:center;gap:7px;min-height:30px;padding:0 11px;border-radius:6px;border:1px solid transparent;background:none;color:var(--ink2);font-weight:600;font-size:12.5px;cursor:pointer;transition:background-color .15s,color .15s,border-color .15s}.ppx:hover{background:var(--bg);color:var(--ink)}.ppx[aria-selected=true]{background:color-mix(in srgb,var(--series) 10%,var(--card));border-color:color-mix(in srgb,var(--series) 45%,var(--line));color:var(--ink)}.ppx:focus-visible{outline:2px solid var(--series);outline-offset:1px}.ppx i{width:7px;height:7px;border-radius:50%;background:var(--line);flex:none}.ppx i.ok{background:var(--gain);animation:nhip 1.8s ease-out infinite}.ppx i.tk{background:#d99a00}
@keyframes nhip{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--gain) 55%,transparent)}100%{box-shadow:0 0 0 7px transparent}}@keyframes moi{0%{background:color-mix(in srgb,var(--series) 18%,transparent)}100%{background:transparent}}
.pl{display:grid;gap:8px;border-top:1px solid var(--line);padding-top:8px}.plh{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}.plh b{font-size:13.5px}.plh small{color:var(--mute);font-size:12px}.plg{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:6px}.plg div{display:grid;gap:1px;min-width:0;border:1px solid var(--line);border-radius:6px;padding:6px 9px}.plg small{font-size:11.5px;color:var(--mute)}.plg b{font-size:16px;font-variant-numeric:tabular-nums;letter-spacing:-.01em}.plg i{font-style:normal;font-size:11.5px;color:var(--mute);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.plg .sl b{color:var(--loss)}.plg .tp b{color:var(--gain)}.plg .mt{border-style:dashed}.pl .why{margin:0}.pl .why i{font-style:normal}.plk{margin:0;font-size:13px;color:var(--ink2)}.plk b{color:var(--ink)}.pln{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}.pln small{color:var(--mute);font-size:12px}.pln .ictb{margin-top:0}.pl.moi .plg div{animation:moi .9s ease-out}.chartp.max .pl>.why,.chartp.max .pln small{display:none}
.vetb{position:absolute;left:6px;top:30px;z-index:3;display:grid;grid-template-columns:repeat(2,28px);gap:2px;padding:3px;background:color-mix(in srgb,var(--card) 94%,transparent);border:1px solid var(--line);border-radius:8px;box-shadow:0 2px 10px rgba(16,24,40,.1)}.vetb button{display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:6px;background:none;color:var(--ink2);cursor:pointer;transition:background-color .12s,color .12s}.vetb button:hover:not(:disabled){background:var(--bg);color:var(--ink)}.vetb button[aria-pressed=true]{background:var(--series);color:var(--btn-ink)}.vetb button:disabled{opacity:.32;cursor:default}.vetb button:focus-visible{outline:2px solid var(--series);outline-offset:1px}.vetb i{grid-column:1/-1;height:1px;background:var(--line);margin:2px 3px}.vetb .mo{display:none}.vegoi{position:absolute;left:50%;top:30px;transform:translateX(-50%);z-index:3;max-width:70%;background:var(--ink);color:var(--card);font-size:12px;border-radius:6px;padding:5px 10px;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.2)}.vegoi[hidden]{display:none}.venhap{position:absolute;z-index:6;width:220px;font:12.5px Tahoma,'Segoe UI',Arial,sans-serif;padding:5px 8px;border:1px solid var(--series);border-radius:6px;background:var(--card);color:var(--ink);box-shadow:0 6px 18px rgba(16,24,40,.18);outline:0}body[data-ve] #lwo{pointer-events:auto;cursor:crosshair;touch-action:none}@media(max-width:640px){.vetb{top:26px;grid-template-columns:repeat(2,26px)}.vetb button{width:26px;height:26px}.vetb .mo{display:grid}.vetb[data-thu]{grid-template-columns:26px}.vetb[data-thu] button:not(.mo),.vetb[data-thu] i{display:none}.plg div{padding:4px 8px}.plg i{display:none}.ppt{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none}.ppt::-webkit-scrollbar{display:none}.ppx{flex:none}.plg{grid-template-columns:repeat(2,minmax(0,1fr))}.plg b{font-size:15px}.plh small{display:none}}
@media(prefers-reduced-motion:reduce){.ppx i.ok,.pl.moi .plg div{animation:none}.ppx,.vetb button{transition:none}}
"""

JS = r"""
(()=>{const $=s=>document.querySelector(s),C=$('#cv'),X=C.getContext('2d'),R=$('#read');
let D=null,tf='M15',view={n:160,off:0},mouse=null,drag=null,kieu='toi',plan=null,PTR=null,KC=null,kcHien=null,kcCho=0,kcMo=new Set(),AIR=null,dg=2,ma='',HOC=null,hocCho=0,ppBat={},ictVe=true,planTat=1,ppChon='tat',kyLuat=true,mhLoc=false;try{ictVe=localStorage.getItem('so-ict')!=='0';ppChon=localStorage.getItem('so-ppc')||'tat';kyLuat=localStorage.getItem('so-kl')!=='0';mhLoc=localStorage.getItem('so-mh')==='1';Object.assign(ppBat,JSON.parse(localStorage.getItem('so-pp')||'{}'))}catch(e){}const bat=k=>ppBat[k]!==0,ictOn=()=>!!(PTR&&PTR.ict&&PTR.ict.du&&ictVe&&(ppChon==='ict'||(ppChon==='tat'&&bat('ict')&&(!plan||ppKhoa(plan)==='ict'))));
const BO={gon:{ema20:1,ema50:1,bb:0,sr:1,fvg:0,ob:0,tin:0,lenh:1,bot:1,rsi:0},du:{ema20:1,ema50:1,bb:1,sr:1,fvg:1,ob:1,tin:1,lenh:1,bot:1,rsi:1}},on={...BO.gon};
const lenhHien=()=>((D&&D.lenh)||[]).filter(o=>o.loai==='demo'?on.lenh:on.bot);      // lệnh EA demo theo ô "Lệnh đang mở", lệnh bot tín hiệu theo ô riêng
try{kieu=localStorage.getItem('so-kieu3')||'toi';Object.assign(on,JSON.parse(localStorage.getItem('so-on2')||'{}'));ma=new URLSearchParams(location.search).get('ma')||localStorage.getItem('so-ma')||''}catch(e){}
// chế độ ảnh (?anh=1&nk=<id>&tf=<khung>): chỉ biểu đồ và lệnh trong nhật ký, có nhãn thương hiệu, để anh_lenh.py chụp gửi kèm tin Telegram.
const ANH=new URLSearchParams(location.search).get('anh')==='1';if(ANH){const q=new URLSearchParams(location.search).get('tf')||'';if(/^(M1|M5|M15|M30|H1|H4|D1)$/.test(q))tf=q;document.documentElement.classList.add('anh')}
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const defN=()=>Math.max(40,Math.min(160,Math.floor(((C.clientWidth||($('#lw')||C).clientWidth)-70)/7)));   // màn hình hẹp thì vẽ ít nến hơn để nến đủ rộng
const f2=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:2,maximumFractionDigits:2});
const fp=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{minimumFractionDigits:dg,maximumFractionDigits:dg});   // giá, theo số chữ số của mã đang xem
const vn=(t,day)=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',...(day?{}:{hour:'2-digit',minute:'2-digit'})});
const vnN=(t,day)=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',...(day?{}:{hour:'2-digit',minute:'2-digit'})});
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const kv=(k,v)=>`<div class="kv"><span>${k}</span><b>${v}</b></div>`;
// Bảng màu biểu đồ. "mt5": nền đen, nến viền xanh lá, thân nến tăng đen và nến giảm trắng, lưới chấm xám, bid xám, ask đỏ.
function pal(){if(kieu==='toi')return{bg:'#0c0e0a',fg:'#e3e6dd',grid:'#1d1f1b',wick:'#7be000',wickDn:'#ff5a5f',bull:'#7be000',bear:'#ff5a5f',bid:'#8d9286',ask:'#ff5a5f',
  ema20:'#4da3ff',ema50:'#ffb020',mute:'#8d9286',sr:'#a3a89c',fvg:'#f2d94e',ob:'#b388ff',tin:'#f2d94e',tp:'#8dff08',sl:'#ff5a5f',vao:'#08ffb5',rsi:'#4da3ff',tag:'#e3e6dd',tagfg:'#0a0c06'};
 if(kieu==='mt5')return{bg:'#000000',fg:'#ffffff',grid:'#3d4651',wick:'#00ff00',wickDn:'#00ff00',bull:'#000000',bear:'#ffffff',bid:'#a9b4c0',ask:'#ff3b30',
  ema20:'#ffd700',ema50:'#ff8c00',mute:'#b8c0cc',sr:'#b8c0cc',fvg:'#ffd700',ob:'#b388ff',tin:'#ffcc66',tp:'#00ff00',sl:'#ff3b30',vao:'#4da3ff',rsi:'#4da3ff',tag:'#ffffff',tagfg:'#000000'};
 // "sang": nền trắng cố định, nến tăng xanh lá, nến giảm đỏ cam; không đổi theo nền tối của trang để luôn dễ nhìn
 return{bg:'#ffffff',fg:'#1b1f24',grid:'#d5dae1',wick:'#17935b',wickDn:'#e5532d',bull:'#17935b',bear:'#e5532d',bid:'#6b7482',ask:'#e5532d',
  ema20:'#2f6fed',ema50:'#eb6834',mute:'#6b7482',sr:'#5d6673',fvg:'#eda100',ob:'#6250d6',tin:'#7a5a00',tp:'#17935b',sl:'#e5532d',vao:'#2f6fed',rsi:'#2f6fed',tag:'#1b1f24',tagfg:'#ffffff'}}
function fit(){const r=C.getBoundingClientRect(),d=window.devicePixelRatio||1;C.width=Math.round(r.width*d);C.height=Math.round(r.height*d);X.setTransform(d,0,0,d,0,0);draw()}
function win(){const N=D.candles.length,n=Math.max(30,Math.min(view.n,N));view.n=n;view.off=Math.max(0,Math.min(view.off,N-n));const end=N-view.off;return[end-n,end]}
function nice(raw){const m=Math.pow(10,Math.floor(Math.log10(raw)));for(const k of[1,2,2.5,5,10])if(k*m>=raw)return k*m;return raw}
// --- lớp vẽ bằng TradingView Lightweight Charts (Apache-2.0). Không nạp được thư viện, hoặc mở trang với ?ve=cu, thì dùng lớp vẽ canvas bên dưới.
// vùng rê chuột trên lớp phủ: mỗi hình vẽ ghi lại ô của nó và lời giải thích; con trỏ nằm trong ô nào thì hiện khung giải thích của ô đó
const HIT=[],TIP=document.createElement('div');TIP.className='tip';TIP.hidden=true;$('.stage').appendChild(TIP);
function tipVe(pt){if(!pt){TIP.hidden=true;return}let c=null;const dt=h=>(h.x1-h.x0)*(h.y1-h.y0);
 for(const h of HIT)if(pt.x>=h.x0-3&&pt.x<=h.x1+3&&pt.y>=h.y0-3&&pt.y<=h.y1+3&&(!c||h.uu>c.uu||(h.uu===c.uu&&dt(h)<dt(c))))c=h;
 if(!c){TIP.hidden=true;return}TIP.innerHTML='<b>'+c.tieu+'</b>'+c.dong.filter(Boolean).map(d=>'<span>'+d+'</span>').join('');TIP.hidden=false;
 const W=LWE.clientWidth,H=LWE.clientHeight,w=TIP.offsetWidth,h=TIP.offsetHeight;TIP.style.left=Math.max(6,Math.min(pt.x+16,W-w-72))+'px';TIP.style.top=Math.max(30,pt.y+16+h>H-28?pt.y-h-12:pt.y+16)+'px'}
const LWC=window.LightweightCharts,LWE=$('#lw'),LWO=$('#lwo');let LW=null;
try{if(LWC&&LWE&&new URLSearchParams(location.search).get('ve')!=='cu'){document.body.setAttribute('data-lw','1');
  const tz={timeZone:'Asia/Ho_Chi_Minh'},chart=LWC.createChart(LWE,{autoSize:true,rightPriceScale:{borderVisible:false,scaleMargins:{top:.1,bottom:.06}},
   timeScale:{borderVisible:false,timeVisible:true,secondsVisible:false,rightOffset:4,minBarSpacing:.12,
    tickMarkFormatter:(t,loai)=>{const d=new Date(t*1000);return loai===0?d.toLocaleDateString('vi-VN',{...tz,year:'numeric'}):loai===1?d.toLocaleDateString('vi-VN',{...tz,month:'2-digit',year:'numeric'}):loai===2?d.toLocaleDateString('vi-VN',{...tz,day:'2-digit',month:'2-digit'}):d.toLocaleTimeString('vi-VN',{...tz,hour:'2-digit',minute:'2-digit'})}},
   crosshair:{mode:0},localization:{locale:'vi-VN',timeFormatter:t=>vnN(t,tf==='D1'),priceFormatter:p=>fp(p)}});
  const phu={priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false};
  LW={chart,lines:[],key:'',idx:new Map(),rsi:null,nen:chart.addSeries(LWC.CandlestickSeries,{}),
   e20:chart.addSeries(LWC.LineSeries,{...phu,lineWidth:2}),e50:chart.addSeries(LWC.LineSeries,{...phu,lineWidth:2}),
   bbt:chart.addSeries(LWC.LineSeries,{...phu,lineWidth:1,lineStyle:2}),bbd:chart.addSeries(LWC.LineSeries,{...phu,lineWidth:1,lineStyle:2})};
  LW.nen.applyOptions({autoscaleInfoProvider:goc=>{const r=goc();if(r&&r.priceRange&&plan)for(const v of[plan.vao,plan.sl,(plan.tp||[])[0]])if(v!=null){
    r.priceRange.minValue=Math.min(r.priceRange.minValue,v);r.priceRange.maxValue=Math.max(r.priceRange.maxValue,v)}return r}});
  chart.timeScale().subscribeVisibleLogicalRangeChange(()=>{LW.cho=null;lwPhu()});   // khung vừa đặt đã được thư viện áp: đọc lại được
  chart.subscribeCrosshairMove(p=>{LW.hov=!!(p&&p.time!=null);lwDoc(p&&p.time!=null?LW.idx.get(p.time):null);lwPhu();tipVe(p&&p.point)});LWE.addEventListener('pointerleave',()=>tipVe(null));
  LWE.addEventListener('dblclick',()=>lwNay());
  // Lỗi đã gặp (25/11/2026): ở chế độ Toàn màn hình, Chrome không gửi sự kiện cuộn chuột tới biểu đồ (vùng nhận cuộn không cập nhật theo khung
  // position:fixed), nên lăn chuột không thu nhỏ hay phóng to được. Một trình nghe thụ động ở window buộc Chrome luôn gửi sự kiện cuộn xuống trang.
  addEventListener('wheel',()=>{},{capture:true,passive:true})}}
catch(e){LW=null;document.body.removeAttribute('data-lw');console.warn('Không dùng được Lightweight Charts, quay về lớp vẽ cũ:',e)}
function lwDoc(k){if(!D)return;const cs=D.candles;if(k==null||k<0||k>=cs.length)k=cs.length-1;const c=cs[k],P=pal(),g=(arr,nm,co)=>{const v=arr&&(arr[k]!=null?arr[k]:arr[k-1]);return v!=null?` &nbsp;${nm} <b>${(co?f2:fp)(v)}</b>`:''};
 R.style.color=P.fg;R.style.background=kieu!=='sang'?'rgba(0,0,0,.55)':'rgba(255,255,255,.78)';
 R.innerHTML=`<b>${D.khac_vang?esc(D.ma):'XAUUSD'}, ${tf}</b>${k===D.live?' (đang chạy)':''} &nbsp;${vnN(c[0],tf==='D1')} &nbsp;M <b>${fp(c[1])}</b> C <b>${fp(c[2])}</b> T <b>${fp(c[3])}</b> Đ <b>${fp(c[4])}</b>`
  +(LWE.clientWidth<560?'':(on.ema20?g(D.ema20,'EMA20'):'')+(on.ema50?g(D.ema50,'EMA50'):'')+(on.rsi?g(D.rsi,'RSI14',1):''))}
function lwNay(){if(!LW||!D)return;const n=D.candles.length;LW.chart.timeScale().setVisibleLogicalRange({from:n-defN(),to:n+4})}
function lwZoom(f){const ts=LW.chart.timeScale(),r=ts.getVisibleLogicalRange();if(!r)return;ts.setVisibleLogicalRange({from:r.to-Math.max(15,(r.to-r.from)*f),to:r.to})}
function lwCuon(d){const ts=LW.chart.timeScale();ts.scrollToPosition(ts.scrollPosition()+d,false)}
function lwDraw(){const P=pal(),c=LW.chart,cs=D.candles,key=(D.khac_vang?D.ma:'XAU')+'|'+tf,moi=key!==LW.key,ts=c.timeScale(),giu=moi?null:(LW.cho||ts.getVisibleLogicalRange()),mo=h=>h.length===7?h+'99':h;
 c.applyOptions({layout:{background:{type:'solid',color:P.bg},textColor:P.fg,fontFamily:'Tahoma, "Segoe UI", Arial, sans-serif',fontSize:11,attributionLogo:true},
  grid:{vertLines:{color:P.grid,style:1},horzLines:{color:P.grid,style:1}}});
 LW.nen.applyOptions({upColor:P.bull,downColor:P.bear,wickUpColor:P.wick,wickDownColor:P.wickDn,borderUpColor:P.wick,borderDownColor:P.wickDn,priceLineColor:P.bid,
  priceFormat:{type:'price',precision:dg,minMove:Math.pow(10,-dg)}});
 LW.idx.clear();
 LW.nen.setData(cs.map((k,i)=>{LW.idx.set(k[0],i);const u=k[4]>=k[1],o={time:k[0],open:k[1],high:k[2],low:k[3],close:k[4]};
  if(i===D.live){o.color=mo(u?P.bull:P.bear);o.wickColor=mo(u?P.wick:P.wickDn);o.borderColor=mo(u?P.wick:P.wickDn)}return o}));
 const duong=(s,arr,col,bat)=>{const co=!!bat&&!!arr;s.applyOptions({color:col,visible:co});if(co)s.setData(cs.map((k,i)=>arr[i]==null?{time:k[0]}:{time:k[0],value:arr[i]}))};
 duong(LW.e20,D.ema20,P.ema20,on.ema20);duong(LW.e50,D.ema50,P.ema50,on.ema50);duong(LW.bbt,D.bb_tren,P.mute,on.bb);duong(LW.bbd,D.bb_duoi,P.mute,on.bb);
 if(on.rsi&&D.rsi){if(!LW.rsi){LW.rsi=c.addSeries(LWC.LineSeries,{lineWidth:2,priceLineVisible:false,lastValueVisible:true,priceFormat:{type:'price',precision:1,minMove:.1}},1);
   for(const m of[70,30])LW.rsi.createPriceLine({price:m,color:P.mute,lineWidth:1,lineStyle:1,axisLabelVisible:true,title:''});try{c.panes()[1].setHeight(96)}catch(e){}}
  LW.rsi.applyOptions({color:P.rsi});LW.rsi.setData(cs.map((k,i)=>D.rsi[i]==null?{time:k[0]}:{time:k[0],value:D.rsi[i]}))}
 else if(LW.rsi){c.removeSeries(LW.rsi);LW.rsi=null}
 for(const l of LW.lines)LW.nen.removePriceLine(l);LW.lines=[];LW.nhan=[];
 const ngang=(price,color,title,style,w,nhan)=>{if(price!=null)LW.lines.push(LW.nen.createPriceLine({price,color,lineWidth:w||1,lineStyle:style,axisLabelVisible:nhan!==false,title:title||''}))};
 if(plan){const tps=(plan.tp||[]).slice(0,3);ngang(plan.vao,P.vao,'Vào '+(plan.huong==='MUA'?'MUA':'BÁN')+(plan.hieu_luc===false?(plan.cu?' lúc tín hiệu (đã qua)':' (tham khảo)'):''),3,2);
  ngang(plan.sl,P.sl,'SL −'+fp(plan.rui_ro_gia),3,2);tps.forEach((v,i)=>ngang(v,P.tp,'TP'+(tps.length>1?(i+1):'')+(plan.rr&&plan.rr[i]!=null?' '+f2(plan.rr[i])+'R':''),3,2));if(plan.muc_tieu)ngang(plan.muc_tieu.gia,P.ob,'Mục tiêu lý thuyết '+f2(plan.muc_tieu.r)+'R',1,1)}
 else{const tkv=tkLenh().map(x=>x.vao);for(const o of lenhHien()){if(tkv.some(v=>Math.abs(v-o.vao)<.011))continue;ngang(o.vao,P.vao,o.nhan,4,1);ngang(o.sl,P.sl,'SL '+o.nhan,4,1)}}
 if(on.sr){const cuoi=a=>{if(!a)return null;for(let i=a.length-1;i>=0;i--)if(a[i]!=null)return a[i];return null};
  const kc=cuoi(D.khang_cu),ht=cuoi(D.ho_tro);ngang(kc,P.sr,'',2,1,false);ngang(ht,P.sr,'',2,1,false);if(kc!=null)LW.nhan.push([kc,P.sr,'Kháng cự 2 giờ '+fp(kc),-5,'left']);if(ht!=null)LW.nhan.push([ht,P.sr,'Hỗ trợ 2 giờ '+fp(ht),-5,'left']);
  const lb=D.luat&&D.luat.bot,tr=lb&&lb.trend,c0=!D.khac_vang&&tr&&((D.luat.bot_cho||[]).find(x=>x.tf===tf)||(D.luat.bot_cho||[])[0]);
  if(c0){const m=tr>0?c0.dinh:c0.day;ngang(m,P.vao,'',1,1,false);LW.nhan.push([m,P.vao,'Bot '+(tr>0?'MUA':'BÁN')+' nếu nến '+c0.tf+' đóng '+(tr>0?'trên ':'dưới ')+fp(m),12,'left'])}}
 LW.askL=null;if(D.nguon==='mt5'&&D.ask){ngang(D.ask,P.ask,'',0,1);LW.askL=LW.lines[LW.lines.length-1]}LW.tCuoi=cs[cs.length-1][0];
 let xem=giu;if(giu&&LW.t0!=null&&cs[0][0]<LW.t0){const k=LW.idx.get(LW.t0);if(k>0)xem={from:giu.from+k,to:giu.to+k}}LW.t0=cs[0][0];
 if(moi){LW.key=key;lwNay()}else if(xem)ts.setVisibleLogicalRange(xem);
 lwDoc(null);requestAnimationFrame(lwPhu)}
// lớp phủ: vùng rủi ro và lợi nhuận của phương án, vùng giá gần nhất, giờ tin, và các lần luật ra lệnh trước đây
function lwPhu(){if(!LW||!D||!D.candles.length)return;const d=window.devicePixelRatio||1,W=LWE.clientWidth,H=LWE.clientHeight,c=LW.chart,ts=c.timeScale(),cs=D.candles,P=pal();
 if(LWO.width!==Math.round(W*d)||LWO.height!==Math.round(H*d)){LWO.width=Math.round(W*d);LWO.height=Math.round(H*d)}LWO.style.width=W+'px';LWO.style.height=H+'px';
 const X=LWO.getContext('2d');X.setTransform(d,0,0,d,0,0);X.clearRect(0,0,W,H);let pw=W-64,ph=H-26;try{pw=W-c.priceScale('right').width()}catch(e){}try{ph=c.panes()[0].getHeight()}catch(e){}
 const y=v=>LW.nen.priceToCoordinate(v),dt=cs.length>1?cs[1][0]-cs[0][0]:900,
  vt=t=>{let a=0,b=cs.length-1;if(t>cs[b][0])return b+(t-cs[b][0])/dt;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}return a},xl=i=>ts.logicalToCoordinate(i);
 X.save();X.beginPath();X.rect(0,0,pw,ph);X.clip();
 const hop=(x0,p1,p2,col,a)=>{const y1=y(p1),y2=y(p2);if(y1==null||y2==null||x0==null||x0>pw)return;x0=Math.max(0,x0);X.globalAlpha=a;X.fillStyle=col;X.fillRect(x0,Math.min(y1,y2),pw-x0,Math.max(2,Math.abs(y2-y1)));X.globalAlpha=1};
 const px0=D.bid||cs[cs.length-1][4],zs=(D.vung||[]).filter(z=>on[z.loai]),
  gan=[zs.filter(z=>z.duoi>px0).sort((p,q)=>p.duoi-q.duoi)[0],zs.filter(z=>z.tren<px0).sort((p,q)=>q.tren-p.tren)[0],zs.find(z=>z.duoi<=px0&&z.tren>=px0)].filter(Boolean);
 for(const z of gan)hop(xl(vt(z.t)),z.duoi,z.tren,z.loai==='fvg'?P.fvg:P.ob,kieu!=='sang'?.22:.15);
 if(on.tin){X.strokeStyle=P.tin;X.setLineDash([3,4]);for(const t of D.tin||[]){const xx=xl(vt(t));if(xx==null||xx<0||xx>pw)continue;X.beginPath();X.moveTo(Math.round(xx)+.5,0);X.lineTo(Math.round(xx)+.5,ph);X.stroke()}X.setLineDash([])}
 const plT=plan&&(plan.nen?Date.parse(plan.nen)/1000:plan.nk?Date.parse(plan.nk.luc)/1000:null),plXt=plT?xl(vt(plT)):null,plX=plan?(plXt!=null?Math.max(96,Math.min(plXt,pw-420)):Math.round(pw*.55)):0;
 if(plan){const x0=plX,tps=(plan.tp||[]).slice(0,3);if(plan.vung)hop(0,plan.vung[0],plan.vung[1],P.vao,.14);
  if(plan.sl!=null)hop(x0,plan.vao,plan.sl,P.sl,.16);if(tps.length)hop(x0,plan.vao,tps[tps.length-1],P.tp,.16)}
 // --- hình vẽ của phương án và bản đồ ICT. Mỗi hình ghi vùng rê chuột (HIT); nhãn gom vào NH rồi đặt sau cùng để không đè nhau.
 HIT.length=0;const NH=[],atr=PTR&&PTR.boi_canh&&PTR.boi_canh.atr_m15,soA=v=>atr?' ('+f2(Math.abs(v)/atr)+' ATR)':'',gia0=(PTR&&PTR.bid)||px0,
  o=(x0,y0,x1,y1,tieu,dong,uu)=>HIT.push({x0:Math.min(x0,x1),y0:Math.min(y0,y1),x1:Math.max(x0,x1),y1:Math.max(y0,y1),tieu,dong,uu:uu||0}),cach=v=>'Cách giá hiện tại '+fp(Math.abs(v-gia0))+soA(v-gia0)+'.';
 if(plan){const x0=plX,tps=(plan.tp||[]).slice(0,3),yv=y(plan.vao),ys=plan.sl==null?null:y(plan.sl),yt=tps.length?y(tps[tps.length-1]):null,hg=plan.huong==='MUA'?'MUA':'BÁN',rr=plan.sl==null?null:Math.abs(plan.vao-plan.sl),
   hl=plan.hieu_luc===false?'Chỉ để tham khảo: '+esc((plan.vi_sao_het||[]).join(' ')):plan.hieu_luc?'Còn hiệu lực lúc phân tích.':'';
  if(yv!=null&&ys!=null)o(x0,yv,pw,ys,'Vùng rủi ro của phương án '+hg,[esc(plan.ten||''),'Vào '+fp(plan.vao)+' · dừng lỗ '+fp(plan.sl)+', cách '+fp(rr)+soA(rr)+'.','Giá chạm '+fp(plan.sl)+' thì phương án sai. Lệnh chờ chưa khớp mà giá chạm mức này thì hủy lệnh.',hl],1);
  if(yv!=null&&yt!=null)o(x0,yv,pw,yt,'Vùng lợi nhuận của phương án '+hg,[esc(plan.ten||''),tps.map((v,i)=>'TP'+(tps.length>1?i+1:'')+' '+fp(v)+(plan.rr&&plan.rr[i]!=null?' ('+f2(plan.rr[i])+'R)':'')).join(' · '),esc(plan.ly_do||''),hl],1)}
 if(ictOn()){const I=PTR.ict,mt=kieu!=='sang',cTK=P.ob,nho=dt<=3600;
  const vach=(v,t0,col,dash,chu,duoi,uu,tieu,dong)=>{if(v==null)return;const yy=y(v);if(yy==null)return;let x0=t0?xl(vt(t0)):0;if(x0==null||x0<0)x0=0;if(x0>pw-60)x0=pw-60;const Y=Math.round(yy)+.5;
   X.strokeStyle=col;X.lineWidth=1;X.setLineDash(dash);X.beginPath();X.moveTo(x0,Y);X.lineTo(pw,Y);X.stroke();X.setLineDash([]);NH.push([chu,t0?x0+4:76,duoi?Y+13:Y-4,col,uu]);o(x0,Y-6,pw,Y+6,tieu,dong,3)};
  // khoảng trống giá: chỉ vẽ vùng đang chứa giá và hai vùng gần giá nhất mỗi phía
  const fs=I.fvg||[],chon=[...fs.filter(z=>z.duoi<=gia0&&z.tren>=gia0),...fs.filter(z=>z.duoi>gia0).sort((a,b)=>a.duoi-b.duoi).slice(0,2),...fs.filter(z=>z.tren<gia0).sort((a,b)=>b.tren-a.tren).slice(0,2)];
  for(const z of chon){const g=z.huong==='giam',col=g?P.sl:P.tp,x0=xl(vt(z.t)),y1=y(z.tren),y2=y(z.duoi);hop(x0,z.duoi,z.tren,col,mt?.2:.12);if(y1==null||y2==null||x0==null||x0>pw)continue;
   NH.push(['FVG '+(g?'giảm':'tăng'),Math.max(x0+6,pw-230),(y1+y2)/2+4,col,2]);
   o(Math.max(0,x0),y1,pw,y2,'Khoảng trống giá '+(g?'giảm':'tăng')+' (FVG)',[fp(z.duoi)+' – '+fp(z.tren)+' · rộng '+fp(z.tren-z.duoi)+soA(z.tren-z.duoi)+'.','Tạo lúc '+vn(z.t)+'. '+(z.da_cham?'Giá đã quay lại chạm một phần, chưa lấp hết.':'Giá chưa quay lại chạm.'),cach((z.duoi+z.tren)/2),
    g?'Nhịp giảm mạnh để lại vùng chưa khớp lệnh. ICT coi đây là chỗ giá hay hồi lên trước khi giảm tiếp; nến đóng vượt hẳn lên trên vùng thì vùng hết ý nghĩa.':'Nhịp tăng mạnh để lại vùng chưa khớp lệnh. ICT coi đây là chỗ giá hay hồi xuống trước khi tăng tiếp; nến đóng thủng hẳn xuống dưới vùng thì vùng hết ý nghĩa.'],0)}
  vach(I.can_bang,I.t_bien,P.mute,[2,4],'EQ 50%',0,1,'Mức 50% của biên độ 24 giờ (EQ) '+fp(I.can_bang),['Biên độ 24 giờ: '+fp((I.bien||[])[0])+' – '+fp((I.bien||[])[1])+'.','Giá đang ở nửa '+(I.vi_tri==='premium'?'trên (premium).':'dưới (discount).'),'Theo ICT: bán nên ở premium (giá đắt), mua nên ở discount (giá rẻ). Đây là phần hợp lưu, chưa được đo riêng.']);
  vach(I.dinh_hom_truoc,0,P.mute,[1,4],'PDH '+fp(I.dinh_hom_truoc),0,1,'Đỉnh hôm trước (PDH) '+fp(I.dinh_hom_truoc),['Mức cao nhất của ngày giao dịch trước, tính theo giờ máy chủ (UTC).','Lệnh dừng lỗ và lệnh chờ hay dồn quanh mức này, nên giá thường tìm tới đây.',I.dinh_hom_truoc==null?'':cach(I.dinh_hom_truoc)]);
  vach(I.day_hom_truoc,0,P.mute,[1,4],'PDL '+fp(I.day_hom_truoc),1,1,'Đáy hôm trước (PDL) '+fp(I.day_hom_truoc),['Mức thấp nhất của ngày giao dịch trước, tính theo giờ máy chủ (UTC).','Lệnh dừng lỗ và lệnh chờ hay dồn quanh mức này, nên giá thường tìm tới đây.',I.day_hom_truoc==null?'':cach(I.day_hom_truoc)]);
  vach(I.bsl,I.t_tk,cTK,[6,4],'BSL '+fp(I.bsl),0,5,'Thanh khoản phía trên (BSL) '+fp(I.bsl),['Đỉnh cao nhất của 5 giờ gần nhất (20 nến M15).','Lệnh dừng lỗ của phe bán thường nằm ngay trên mức này.','Giá vượt lên rồi nến M15 đóng trở lại bên dưới là một lần quét thanh khoản: điều kiện của mô hình BÁN.',cach(I.bsl)]);
  vach(I.ssl,I.t_tk,cTK,[6,4],'SSL '+fp(I.ssl),1,5,'Thanh khoản phía dưới (SSL) '+fp(I.ssl),['Đáy thấp nhất của 5 giờ gần nhất (20 nến M15).','Lệnh dừng lỗ của phe mua thường nằm ngay dưới mức này.','Giá thủng xuống rồi nến M15 đóng trở lại bên trên là một lần quét thanh khoản: điều kiện của mô hình MUA.',cach(I.ssl)]);
  if(nho)for(const s of(I.cau_truc||[]).slice(-4)){const x0=xl(vt(s.t0)),x1=xl(vt(s.t)),yy=y(s.gia);if(x0==null||x1==null||yy==null||x1<0)continue;const Y=Math.round(yy)+.5,tg=s.huong==='tang',w=X.measureText(s.loai).width;
   X.strokeStyle=P.fg;X.lineWidth=1;X.beginPath();X.moveTo(x0,Y);X.lineTo(x1,Y);X.stroke();NH.push([s.loai,(x0+x1)/2-w/2,tg?Y-4:Y+13,P.fg,4]);
   o(x0,Y-15,x1,Y+15,s.loai+' '+(tg?'tăng':'giảm')+' tại '+fp(s.gia),[s.loai==='BOS'?'Phá cấu trúc cùng chiều (BOS): cấu trúc M15 tiếp tục '+(tg?'tăng.':'giảm.'):'Đổi chiều cấu trúc (CHoCH): cấu trúc M15 chuyển từ '+(tg?'giảm sang tăng.':'tăng sang giảm.'),
    'Nến M15 mở lúc '+vn(s.t)+' đóng '+(tg?'vượt đỉnh ':'thủng đáy ')+fp(s.gia)+'; '+(tg?'đỉnh':'đáy')+' đó hình thành lúc '+vn(s.t0)+'.','Đỉnh và đáy được xác nhận khi có 3 nến mỗi bên, nên có thể khác cách bạn vẽ tay.'],4)}
  if(nho)for(const q of I.quet||[]){const xx=xl(vt(q.t)),yy=y(q.gia);if(xx==null||yy==null)continue;const dn=q.loai==='dinh',Y=dn?yy-7:yy+7;
   X.strokeStyle=cTK;X.lineWidth=1.8;X.beginPath();X.moveTo(xx-4,Y-4);X.lineTo(xx+4,Y+4);X.moveTo(xx+4,Y-4);X.lineTo(xx-4,Y+4);X.stroke();X.lineWidth=1;
   o(xx-9,Y-9,xx+9,Y+9,'Quét '+(dn?'đỉnh':'đáy')+' tại '+fp(q.gia),['Nến M15 mở lúc '+vn(q.t)+': giá '+(dn?'vượt đỉnh':'thủng đáy')+' 5 giờ rồi đóng trở lại '+(dn?'bên dưới.':'bên trên.'),
    dn?'Lệnh dừng lỗ của phe bán vừa bị lấy. ICT coi đây là dấu hiệu sớm của một nhịp giảm; cần thêm một khoảng trống giá giảm mới thành điểm vào.':'Lệnh dừng lỗ của phe mua vừa bị lấy. ICT coi đây là dấu hiệu sớm của một nhịp tăng; cần thêm một khoảng trống giá tăng mới thành điểm vào.'],5)}}
 // --- lệnh của tài khoản MT5 demo trên mã đang xem: đang mở, đang chờ và đã đóng
 if(plan&&y(plan.vao)!=null){const x0=plX,yv=y(plan.vao),mua=plan.huong==='MUA',tps=(plan.tp||[]).slice(0,3),ys=plan.sl==null?null:y(plan.sl),rr=plan.sl==null?null:Math.abs(plan.vao-plan.sl);
  X.fillStyle=P.vao;X.strokeStyle=P.bg;X.lineWidth=1.6;X.setLineDash([]);X.beginPath();if(mua){X.moveTo(x0,yv-10);X.lineTo(x0-8,yv+6);X.lineTo(x0+8,yv+6)}else{X.moveTo(x0,yv+10);X.lineTo(x0-8,yv-6);X.lineTo(x0+8,yv-6)}X.closePath();X.fill();X.stroke();
  NH.push([(mua?'▲ Vào MUA ':'▼ Vào BÁN ')+fp(plan.vao)+(plan.cu?' · giá lúc tín hiệu':''),x0+14,yv+(mua?-7:16),P.vao,12,1]);
  if(ys!=null)NH.push(['Ra · dừng lỗ '+fp(plan.sl)+' (−'+fp(rr)+')',x0+14,(yv+ys)/2+4,P.sl,11,1]);
  tps.forEach((v,i)=>{const yy=y(v);if(yy!=null)NH.push(['Ra · chốt lời'+(tps.length>1?' '+(i+1):'')+' '+fp(v)+' (+'+fp(Math.abs(v-plan.vao))+(plan.rr&&plan.rr[i]!=null?' · '+f2(plan.rr[i])+'R':'')+')',x0+14,yy+(mua?15:-6),P.tp,11,1])});
  NH.push([(mua?'MUA':'BÁN')+' · '+(plan.ten||'')+(plan.cu?' · đã quá hạn'+(plan.kc==='sl'?', giá đã chạm dừng lỗ':plan.kc==='tp'?', giá đã chạm chốt 2R':''):plan.hieu_luc===false?' · chỉ để tham khảo':plan.hieu_luc?' · còn hiệu lực':''),pw,48,P.fg,13,1])}
 else if(PTR&&!plan)NH.push(['Chưa có điểm vào lúc này'+(ppChon==='tat'?'':' theo phương pháp đang chọn'),pw,48,P.mute,13,1]);
 if(PTR&&!ANH){for(const q of ppNhom('tat').filter(q=>q.co&&(!plan||q.ma!==plan.ma)).slice(0,3)){const yy=y(q.vao);if(yy==null)continue;const mua=q.huong==='MUA';
   NH.push([(mua?'▲ ':'▼ ')+(q.ten_ngan||q.ten)+' '+fp(q.vao)+(q.hieu_luc?'':' (tham khảo)'),76,yy+4,P.mute,3]);
   o(70,yy-9,340,yy+9,'Điểm vào khác: '+esc(q.ten),[(mua?'MUA ':'BÁN ')+fp(q.vao)+' · dừng lỗ '+fp(q.sl)+' · chốt lời '+fp(q.tp[q.tp.length-1])+'.','Bấm nút của phương pháp này ở thanh phía trên biểu đồ để vẽ đầy đủ.'],2)}}
 if(TK&&TK.san_sang&&on.lenh&&!ANH){const sym=tkMa(),tien=v=>(v>0?'+':v<0?'−':'')+f2(Math.abs(v))+' '+TK.tien,x0=Math.round(pw*.42);
  for(const l of tkLenh()){const mua=l.huong==='MUA',yv=y(l.vao);if(yv==null)continue;const Y=Math.round(yv)+.5,col=l.lai>=0?P.tp:P.sl,ten='Tài khoản · '+(mua?'MUA ':'BÁN ')+f2(l.lot)+' lot';
   X.strokeStyle=P.vao;X.lineWidth=1.5;X.setLineDash([]);X.beginPath();X.moveTo(0,Y);X.lineTo(pw,Y);X.stroke();NH.push([ten+' · '+fp(l.vao)+' · '+tien(l.lai),x0,Y-4,col,8]);
   o(0,Y-6,pw,Y+6,ten+' tại '+fp(l.vao),['Lãi lỗ đang treo: '+tien(l.lai)+(l.swap?' (phí qua đêm '+tien(l.swap)+')':'')+'. Giá hiện tại '+fp(l.gia)+'.','Mở lúc '+esc(l.mo)+(l.nguon?' · nguồn: '+esc(l.nguon):'')+'.',
    'Dừng lỗ '+(l.sl!=null?fp(l.sl):'chưa đặt')+' · chốt lời '+(l.tp!=null?fp(l.tp):'chưa đặt')+(l.rui_ro!=null?' · chạm dừng lỗ thì mất '+f2(l.rui_ro)+' '+TK.tien:'')+'.','Đọc từ tài khoản demo; trang không đặt, sửa hay đóng lệnh.'],7);
   for(const[v,c2,nh]of[[l.sl,P.sl,'Tài khoản · dừng lỗ '],[l.tp,P.tp,'Tài khoản · chốt lời ']]){const yy=v==null?null:y(v);if(yy==null)continue;const Y2=Math.round(yy)+.5;X.strokeStyle=c2;X.lineWidth=1.2;X.setLineDash([6,4]);X.beginPath();X.moveTo(x0,Y2);X.lineTo(pw,Y2);X.stroke();X.setLineDash([]);NH.push([nh+fp(v),x0,Y2-4,c2,8])}}
  for(const c of(TK.cho||[]).filter(x=>x.ma===sym)){const yy=y(c.gia);if(yy==null)continue;const Y=Math.round(yy)+.5;X.strokeStyle=P.vao;X.lineWidth=1.2;X.setLineDash([2,3]);X.beginPath();X.moveTo(0,Y);X.lineTo(pw,Y);X.stroke();X.setLineDash([]);
   NH.push(['Tài khoản · lệnh chờ '+c.loai+' '+f2(c.lot)+' lot · '+fp(c.gia),x0,Y-4,P.vao,8]);o(0,Y-6,pw,Y+6,'Lệnh chờ '+esc(c.loai)+' '+f2(c.lot)+' lot tại '+fp(c.gia),['Đặt lúc '+esc(c.dat)+(c.nguon?' · nguồn: '+esc(c.nguon):'')+'.','Dừng lỗ '+(c.sl!=null?fp(c.sl):'chưa đặt')+' · chốt lời '+(c.tp!=null?fp(c.tp):'chưa đặt')+'.'],7)}
  for(const d2 of(TK.da_dong||[]).filter(x=>x.ma===sym)){const t=Date.parse(d2.luc)/1000;if(t<cs[0][0])continue;const xx=xl(vt(t)),yy=y(d2.gia);if(xx==null||yy==null)continue;const col=d2.lai>=0?P.tp:P.sl;
   X.fillStyle=col;X.strokeStyle=P.bg;X.lineWidth=1.2;X.beginPath();X.moveTo(xx,yy-6);X.lineTo(xx+6,yy);X.lineTo(xx,yy+6);X.lineTo(xx-6,yy);X.closePath();X.fill();X.stroke();
   o(xx-8,yy-8,xx+8,yy+8,'Đã đóng lệnh '+(d2.huong==='MUA'?'MUA ':'BÁN ')+f2(d2.lot)+' lot: '+tien(d2.lai),['Đóng tại '+fp(d2.gia)+' lúc '+vn(t)+(d2.nguon?' · nguồn: '+esc(d2.nguon):'')+'.','Lãi lỗ đã trừ phí và phí qua đêm. Đọc từ lịch sử tài khoản demo.'],7)}}
 if(plan&&plan.nk){const x=plan.nk,moc=[[x.luc,'Ghi lúc '],[x.cho?x.khop:null,'Khớp lúc '],[x.ra,'Xong lúc ']];for(const[t,nh]of moc){if(!t)continue;const g=Date.parse(t)/1000,xx=xl(vt(g));if(xx==null||xx<0||xx>pw)continue;X.strokeStyle=P.vao;X.lineWidth=1;X.setLineDash([3,3]);X.beginPath();X.moveTo(Math.round(xx)+.5,0);X.lineTo(Math.round(xx)+.5,ph);X.stroke();X.setLineDash([]);NH.push([nh+vn(g),xx+5,ph-(nh[0]==='G'?8:nh[0]==='K'?24:40),P.vao,9])}}
 // --- sóng Elliott: cách đếm 0-1-2 của phương án đang vẽ, hoặc cách đếm đang hình thành khi chưa có điểm vào
 {const pe=PTR&&(PTR.phuong_phap||[]).find(x=>x.ma==='elliott'),ch=pe&&!pe.co&&pe.cho,
   E=plan&&plan.song?{song:plan.song,huong:plan.huong,mt:plan.muc_tieu&&plan.muc_tieu.gia}:ch&&(ppChon==='elliott'||(ppChon==='tat'&&!plan&&bat('elliott')))?{song:ch.song||[],huong:ch.huong,mt:ch.muc_tieu,kh:ch.kich_hoat}:null;
  if(E&&E.song.length){const col=P.vao,mua=E.huong==='MUA',pts=E.song.map(q=>[xl(vt(q.t)),y(q.gia),q]).filter(q=>q[0]!=null&&q[1]!=null),cuoi=pts[pts.length-1],
    loi={'0':'Điểm bắt đầu sóng 1. Quy tắc Elliott: sóng 2 không được hồi quá mức này; nếu quá thì cách đếm sai.','1':'Cuối sóng 1. Nến M15 đóng vượt mức này là xác nhận sóng 3, và là điểm vào của phương pháp.','2':'Cuối sóng 2 (hồi 38,2–78,6% của sóng 1). Dừng lỗ đặt ngay sau mức này.'};
   X.strokeStyle=col;X.lineWidth=1.7;X.setLineDash([]);X.beginPath();pts.forEach((q,i)=>i?X.lineTo(q[0],q[1]):X.moveTo(q[0],q[1]));X.stroke();
   if(cuoi&&E.mt!=null&&pts.length>=3){const ym=y(E.mt),xm=Math.min(pw-70,cuoi[0]+Math.max(70,(cuoi[0]-pts[0][0])*.7));if(ym!=null){X.setLineDash([5,4]);X.beginPath();X.moveTo(cuoi[0],cuoi[1]);X.lineTo(xm,ym);X.stroke();X.setLineDash([]);
     NH.push(['(3) '+fp(E.mt),xm+6,ym+4,col,5]);o(xm-12,ym-12,xm+96,ym+12,'Mục tiêu sóng 3: '+fp(E.mt),['Sóng 3 thường là sóng mạnh nhất. Mục tiêu lý thuyết bằng 1,618 lần sóng 1, tính từ cuối sóng 2.','Đây là mức tham chiếu theo sách, không phải lời hứa giá sẽ tới.'],5)}}
   for(const q of pts){const nh=q[2].nhan;if(!nh)continue;const tren=mua===(nh==='1');NH.push(['('+nh+')',q[0]-8,q[1]+(tren?-8:17),col,6]);X.fillStyle=col;X.beginPath();X.arc(q[0],q[1],3,0,7);X.fill();
    o(q[0]-13,q[1]-20,q[0]+13,q[1]+20,'Sóng Elliott · điểm ('+nh+') '+fp(q[2].gia),[loi[nh],'Lúc '+vn(q[2].t)+'. Đỉnh và đáy lấy theo zigzag: mỗi lần đảo chiều ít nhất 2 ATR.'],6)}
   if(E.kh!=null){const yk=y(E.kh);if(yk!=null){const Y=Math.round(yk)+.5;X.strokeStyle=col;X.lineWidth=1;X.setLineDash([2,3]);X.beginPath();X.moveTo(cuoi?cuoi[0]:0,Y);X.lineTo(pw,Y);X.stroke();X.setLineDash([]);
     NH.push(['Elliott: '+(mua?'MUA':'BÁN')+' khi nến M15 đóng '+(mua?'trên ':'dưới ')+fp(E.kh),Math.max(76,(cuoi?cuoi[0]:0)+8),mua?Y-4:Y+13,col,5])}}}}
 // --- nhãn: có nền mờ để đọc được khi nằm trên nến; nhãn nào đè lên nhãn đã đặt thì dời lên hoặc xuống một dòng, vẫn đè thì bỏ
 X.font='11px Tahoma,"Segoe UI",Arial,sans-serif';X.textBaseline='alphabetic';X.textAlign='left';const O=[[0,ph-46,92,ph]],de=(a,b,c2,d2)=>O.some(r=>a<r[2]&&c2>r[0]&&b<r[3]&&d2>r[1]),
  the=v=>{const yy=v==null?null:y(v);if(yy!=null)O.push([pw-150,yy-9,pw,yy+9])};      // chừa chỗ cho thẻ giá mà thư viện vẽ sát thang giá
 if(plan){the(plan.vao);the(plan.sl);(plan.tp||[]).slice(0,3).forEach(the)}else for(const l of lenhHien()){the(l.vao);the(l.sl)}
 const dat=(t,x,yy,col,dam)=>{X.font=(dam?'bold 12px ':'11px ')+'Tahoma,"Segoe UI",Arial,sans-serif';const w=X.measureText(t).width;x=Math.max(4,Math.min(x,pw-w-(dam?158:8)));for(const k of[0,-14,14]){const Y=yy+k;if(Y<34||Y>ph-2||de(x-3,Y-11,x+w+3,Y+3))continue;
   O.push([x-3,Y-11,x+w+3,Y+3]);X.globalAlpha=.84;X.fillStyle=P.bg;X.fillRect(x-3,Y-11,w+6,14);X.globalAlpha=1;X.fillStyle=col;X.fillText(t,x,Y);return}};
 for(const[v,col,chu,lech,can]of LW.nhan||[]){const yy=y(v);if(yy!=null)dat(chu,can==='left'?76:pw-6-X.measureText(chu).width,yy+lech,col)}
 for(const[t,x,yy,col,,dam]of NH.sort((a,b)=>b[4]-a[4]))dat(t,x,yy,col,dam);
 if(KC&&KC.san_sang&&kcHien&&KC.luat[kcHien]&&!D.khac_vang){const r=ts.getVisibleLogicalRange(),sz=5.5;if(r)for(const[t,h,v,u]of KC.luat[kcHien].diem){if(t<cs[0][0])continue;const i=vt(t);if(i<r.from-1||i>r.to+1)continue;
   const xx=xl(i),yy=y(v);if(xx==null||yy==null)continue;X.fillStyle=u>0?P.tp:P.sl;X.strokeStyle=P.bg;X.lineWidth=1;X.beginPath();
   if(h>0){X.moveTo(xx,yy-sz);X.lineTo(xx-sz,yy+sz);X.lineTo(xx+sz,yy+sz)}else{X.moveTo(xx,yy+sz);X.lineTo(xx-sz,yy-sz);X.lineTo(xx+sz,yy-sz)}X.closePath();X.fill();X.stroke()}}
 veVe(X,{y,pw,ph,P,cs,dt,ts});
 X.restore()}
function draw(){if(!D||!D.candles.length)return;if(LW){lwDraw();return}const P=pal(),W=C.clientWidth,H=C.clientHeight,PR=70,PB=22,PT=22,RS=on.rsi?96:0,MB=H-PB-RS,[a,b]=win(),cs=D.candles.slice(a,b),n=b-a;
 let lo=1e12,hi=-1e12;for(const c of cs){if(c[3]<lo)lo=c[3];if(c[2]>hi)hi=c[2]}
 if(plan&&!view.off)for(const v of[plan.vao,plan.sl,(plan.tp||[])[0]])if(v!=null){if(v<lo)lo=v;if(v>hi)hi=v}const pad=(hi-lo)*.08||1;lo-=pad;hi+=pad;
 const bw=(W-PR)/n,x=i=>(i-a+.5)*bw,y=v=>PT+(hi-v)/(hi-lo)*(MB-PT),dt=n>1?cs[1][0]-cs[0][0]:900;
 X.fillStyle=P.bg;X.fillRect(0,0,W,H);X.font='11.5px Tahoma,Segoe UI,Arial';X.textBaseline='middle';X.lineWidth=1;
 // lưới chấm và thang giá
 const step=nice((hi-lo)/7);X.strokeStyle=P.grid;X.fillStyle=P.fg;X.setLineDash([1,3]);X.textAlign='left';
 for(let v=Math.ceil(lo/step)*step;v<hi;v+=step){const yy=Math.round(y(v))+.5;X.beginPath();X.moveTo(0,yy);X.lineTo(W-PR,yy);X.stroke();X.fillText(fp(v),W-PR+6,yy)}
 const every=Math.max(1,Math.ceil(n/Math.max(2,Math.floor((W-PR)/100))));X.textAlign='center';
 for(let i=a;i<b;i++)if((i-a)%every===Math.floor(every/2)){const xx=Math.round(x(i))+.5;X.beginPath();X.moveTo(xx,PT);X.lineTo(xx,H-PB);X.stroke();X.fillText(vn(D.candles[i][0],tf==='D1'),xx,H-10)}
 X.setLineDash([]);
 // vạch ngăn ngày (giờ máy chủ = UTC), như MT5
 if(tf!=='D1'&&tf!=='H4'){X.strokeStyle=P.grid;X.setLineDash([4,4]);for(let i=a+1;i<b;i++)if(Math.floor(D.candles[i][0]/86400)!==Math.floor(D.candles[i-1][0]/86400)){const xx=Math.round(x(i)-bw/2)+.5;X.beginPath();X.moveTo(xx,PT);X.lineTo(xx,MB);X.stroke()}X.setLineDash([])}
 X.strokeStyle=P.grid;X.strokeRect(.5,.5,W-PR-.5,H-PB-.5);if(RS){X.beginPath();X.moveTo(0,MB+.5);X.lineTo(W-PR,MB+.5);X.stroke()}
 X.save();X.beginPath();X.rect(0,PT-8,W-PR,MB-PT+8);X.clip();
 const xt=t=>{let i=D.candles.findIndex(c=>c[0]>=t);if(i<0)i=D.candles.length+(t-D.candles[D.candles.length-1][0])/dt;return x(i)};
 const px0=D.bid||D.candles[D.candles.length-1][4],zs=(D.vung||[]).filter(z=>on[z.loai]),
  gan=[zs.filter(z=>z.duoi>px0).sort((p,q)=>p.duoi-q.duoi)[0],zs.filter(z=>z.tren<px0).sort((p,q)=>q.tren-p.tren)[0],zs.find(z=>z.duoi<=px0&&z.tren>=px0)].filter(Boolean);
 for(const z of gan){const x0=Math.max(0,xt(z.t)-bw/2);if(x0>W-PR||z.tren<lo||z.duoi>hi)continue;
  X.globalAlpha=kieu!=='sang'?.22:.16;X.fillStyle=z.loai==='fvg'?P.fvg:P.ob;X.fillRect(x0,y(z.tren),W-PR-x0,Math.max(2,y(z.duoi)-y(z.tren)));X.globalAlpha=1}
 if(on.tin){X.strokeStyle=P.tin;X.setLineDash([3,4]);for(const t of D.tin||[]){const xx=xt(t);if(xx<0||xx>W-PR)continue;X.beginPath();X.moveTo(xx,PT);X.lineTo(xx,MB);X.stroke()}X.setLineDash([])}
 const line=(arr,col,w,dash,stepped,yf)=>{if(!arr)return;const Y=yf||y;X.strokeStyle=col;X.lineWidth=w;X.setLineDash(dash||[]);X.beginPath();let pen=0,py=0;
  for(let i=a;i<b;i++){const v=arr[i];if(v==null){pen=0;continue}const yy=Y(v);if(!pen){X.moveTo(x(i),yy);pen=1}else{if(stepped)X.lineTo(x(i),py);X.lineTo(x(i),yy)}py=yy}X.stroke();X.setLineDash([]);X.lineWidth=1};
 if(on.bb){line(D.bb_tren,P.mute,1,[2,3]);line(D.bb_duoi,P.mute,1,[2,3])}
 if(on.sr){const seg=(arr,nhan)=>{if(!arr)return;let i=b-1;while(i>=a&&arr[i]==null)i--;if(i<a)return;const v=arr[i];let j=i;while(j>a&&arr[j-1]===v)j--;if(v<lo||v>hi)return;
   const yy=Math.round(y(v))+.5;X.strokeStyle=P.sr;X.setLineDash([6,4]);X.beginPath();X.moveTo(x(j)-bw/2,yy);X.lineTo(W-PR,yy);X.stroke();X.setLineDash([]);
   X.fillStyle=P.sr;X.textAlign='right';X.fillText(nhan,W-PR-6,yy-7);X.textAlign='left'};
  seg(D.khang_cu,'Kháng cự 2 giờ');seg(D.ho_tro,'Hỗ trợ 2 giờ');
  const lb=D.luat&&D.luat.bot,tr=lb&&lb.trend,c0=!D.khac_vang&&tr&&((D.luat.bot_cho||[]).find(c=>c.tf===tf)||(D.luat.bot_cho||[])[0]);
  if(c0){const m=tr>0?c0.dinh:c0.day;if(m>=lo&&m<=hi){const yy=Math.round(y(m))+.5;X.strokeStyle=P.vao;X.lineWidth=1.4;X.setLineDash([2,3]);X.beginPath();X.moveTo(0,yy);X.lineTo(W-PR,yy);X.stroke();
    X.setLineDash([]);X.lineWidth=1;X.fillStyle=P.vao;X.textAlign='left';X.fillText('Bot '+(tr>0?'MUA':'BÁN')+' nếu nến '+c0.tf+' đóng '+(tr>0?'trên ':'dưới ')+fp(m),6,yy+11)}}}
 if(on.ema50)line(D.ema50,P.ema50,1.6);if(on.ema20)line(D.ema20,P.ema20,1.6);
 const cw=Math.max(1,Math.min(15,Math.floor(bw*.7)));
 for(let i=a;i<b;i++){const c=D.candles[i],u=c[4]>=c[1],xx=Math.round(x(i))+.5,col=u?P.wick:P.wickDn;X.globalAlpha=i===D.live?.6:1;X.strokeStyle=col;
  X.beginPath();X.moveTo(xx,y(c[2]));X.lineTo(xx,y(c[3]));X.stroke();const y1=Math.round(y(Math.max(c[1],c[4]))),h=Math.max(1,Math.round(y(Math.min(c[1],c[4])))-y1);
  if(cw>=3){X.fillStyle=u?P.bull:P.bear;X.fillRect(xx-cw/2,y1,cw,h);X.strokeRect(xx-cw/2,y1+.5,cw,Math.max(0,h-1))}}
 X.globalAlpha=1;
 // lệnh đang mở: đường giá vào, SL, TP như trên MT5
 const tags=[],tagsP=[],daO=[];if(!plan)for(const o of lenhHien()){const L=(v,col,t)=>{if(v==null||v<lo||v>hi)return;const yy=Math.round(y(v))+.5;X.strokeStyle=col;X.setLineDash([6,3,1,3]);X.beginPath();X.moveTo(0,yy);X.lineTo(W-PR,yy);X.stroke();X.setLineDash([]);
   tags.push([v,col]);if(daO.some(u=>Math.abs(u-yy)<14))return;daO.push(yy);X.fillStyle=col;X.textAlign='left';X.fillText(t,6,yy-7)};
  L(o.vao,P.vao,nhanL(o)+(o.loai==='demo'?' (demo)':' (tín hiệu)'));L(o.sl,P.sl,'SL · '+nhanL(o))}
 if(KC&&KC.san_sang&&kcHien&&KC.luat[kcHien]){const t0=D.candles[a][0],t1=D.candles[b-1][0]+dt,sz=Math.max(4,Math.min(7,bw*.9));
  for(const[t,d,v,u]of KC.luat[kcHien].diem){if(t<t0||t>=t1||v<lo||v>hi)continue;let i=a,j=b-1;while(i<j){const m=(i+j+1)>>1;if(D.candles[m][0]<=t)i=m;else j=m-1}
   const xx=x(i),yy=y(v);X.fillStyle=u>0?P.tp:P.sl;X.strokeStyle=P.bg;X.lineWidth=1;X.beginPath();
   if(d>0){X.moveTo(xx,yy-sz);X.lineTo(xx-sz,yy+sz);X.lineTo(xx+sz,yy+sz)}else{X.moveTo(xx,yy+sz);X.lineTo(xx-sz,yy-sz);X.lineTo(xx+sz,yy-sz)}X.closePath();X.fill();X.stroke()}}
 if(plan){const xr=W-PR,x0=Math.round(xr*.6),cl=v=>Math.min(hi,Math.max(lo,v)),tps=(plan.tp||[]).slice(0,3),xa=tps.length?tps[tps.length-1]:null,used=[];
  const box=(p1,p2,col)=>{if(p1==null||p2==null)return;const y1=y(cl(p1)),y2=y(cl(p2));X.globalAlpha=.1;X.fillStyle=col;X.fillRect(x0,Math.min(y1,y2),xr-x0,Math.abs(y2-y1));X.globalAlpha=1};
  box(plan.vao,plan.sl,P.sl);box(plan.vao,xa,P.tp);
  if(plan.vung){X.globalAlpha=.16;X.fillStyle=P.vao;X.fillRect(0,y(Math.max(...plan.vung)),xr,Math.max(2,Math.abs(y(plan.vung[0])-y(plan.vung[1]))));X.globalAlpha=1}
  const L2=(v,col,t)=>{if(v==null||v<lo||v>hi)return;const yy=Math.round(y(v))+.5;X.strokeStyle=col;X.lineWidth=1.6;X.setLineDash([9,5]);X.beginPath();X.moveTo(0,yy);X.lineTo(xr,yy);X.stroke();
   X.setLineDash([]);X.lineWidth=1;tagsP.push([v,col]);if(used.some(u=>Math.abs(u-yy)<17))return;used.push(yy);
   X.font='bold 11px Tahoma,Verdana,sans-serif';const w=Math.ceil(X.measureText(t).width)+12;X.fillStyle=col;X.fillRect(x0,yy-8.5,w,17);X.fillStyle='#fff';X.textAlign='left';X.textBaseline='middle';X.fillText(t,x0+6,yy+.5)};
  L2(plan.vao,P.vao,'VÀO '+(plan.huong==='MUA'?'MUA':'BÁN')+(plan.hieu_luc===false?(plan.cu?' lúc tín hiệu (đã qua)':' (tham khảo)'):''));L2(plan.sl,P.sl,'SL · −'+fp(plan.rui_ro_gia));
  tps.forEach((v,i)=>L2(v,P.tp,'TP'+(tps.length>1?(i+1):'')+(plan.rr&&plan.rr[i]!=null?' · '+f2(plan.rr[i])+'R':'')))}
 X.restore();
 const tag=(v,bg,fg)=>{if(v==null||v<lo||v>hi)return;const yy=Math.max(PT+8,Math.min(MB-8,y(v)));X.fillStyle=bg;X.fillRect(W-PR+1,yy-8,PR-2,16);X.fillStyle=fg;X.textAlign='left';X.fillText(fp(v),W-PR+6,yy)};
 {const da=[];for(const[v,col]of[...tagsP,...tags]){if(v==null||v<lo||v>hi)continue;const yy=y(v);if(da.some(u=>Math.abs(u-yy)<16))continue;da.push(yy);tag(v,col,kieu!=='sang'?'#000':'#fff')}}
 const last=D.candles[b-1],songOk=D.nguon==='mt5'&&D.bid&&!view.off,px=songOk?D.bid:last[4];
 if(px>=lo&&px<=hi){const yy=Math.round(y(px))+.5;X.strokeStyle=P.bid;X.beginPath();X.moveTo(0,yy);X.lineTo(W-PR,yy);X.stroke()}
 if(songOk&&D.ask>=lo&&D.ask<=hi){const yy=Math.round(y(D.ask))+.5;X.strokeStyle=P.ask;X.beginPath();X.moveTo(0,yy);X.lineTo(W-PR,yy);X.stroke();tag(D.ask,P.ask,'#fff')}
 tag(px,P.tag,P.tagfg);
 // khung RSI
 if(RS){const r0=MB+6,r1=H-PB-4,ry=v=>r0+(100-v)/100*(r1-r0);X.strokeStyle=P.grid;X.setLineDash([1,3]);X.fillStyle=P.fg;X.textAlign='left';
  for(const v of[30,50,70]){const yy=Math.round(ry(v))+.5;X.beginPath();X.moveTo(0,yy);X.lineTo(W-PR,yy);X.stroke();if(v!==50)X.fillText(v,W-PR+6,yy)}X.setLineDash([]);line(D.rsi,P.rsi,1.4,null,0,ry)}
 let k=b-1;if(mouse&&mouse.x<W-PR){k=Math.max(a,Math.min(b-1,a+Math.floor(mouse.x/bw)));const xx=Math.round(x(k))+.5,yy=Math.round(mouse.y)+.5;X.strokeStyle=P.mute;X.setLineDash([3,3]);
  X.beginPath();X.moveTo(xx,PT);X.lineTo(xx,H-PB);if(yy<MB){X.moveTo(0,yy);X.lineTo(W-PR,yy)}X.stroke();X.setLineDash([]);
  if(yy<MB)tag(hi-(mouse.y-PT)/(MB-PT)*(hi-lo),P.mute,kieu!=='sang'?'#000':'#fff')}
 const c=D.candles[k],g=(arr,nm,co)=>arr&&arr[k]!=null?` &nbsp;${nm} <b>${(co?f2:fp)(arr[k])}</b>`:'';
 R.style.color=P.fg;R.style.background=kieu!=='sang'?'rgba(0,0,0,.55)':'rgba(255,255,255,.78)';
 R.innerHTML=`<b>${D.khac_vang?esc(D.ma):'XAUUSD'}, ${tf}</b>${k===D.live?' (đang chạy)':''} &nbsp;${vn(c[0],tf==='D1')} &nbsp;M <b>${fp(c[1])}</b> C <b>${fp(c[2])}</b> T <b>${fp(c[3])}</b> Đ <b>${fp(c[4])}</b>`
  +(W<560?'':(on.ema20?g(D.ema20,'EMA20'):'')+(on.ema50?g(D.ema50,'EMA50'):'')+(on.rsi?g(D.rsi,'RSI14',1):''))}
const DIR=v=>v>0?'<span class="dir up">▲ TĂNG</span>':v<0?'<span class="dir dn">▼ GIẢM</span>':'<span class="dir">ĐI NGANG</span>';
function botTT(){const el=$('#bot-tt');if(!D){el.innerHTML='';return}
 if(D.khac_vang){el.innerHTML='<b>'+esc(D.ma)+'</b><span>'+(D.chia_se?'Bản chia sẻ: các phương pháp tùy chọn tính theo ATR, đo trên dữ liệu MT5 của chính mã này.':'Luật trong sổ của bạn chỉ dành cho vàng; mã này dùng các phương pháp tùy chọn.')+'</span>';return}
 const L=D.luat||{},b=L.bot;if(!b){el.innerHTML='';return}const tr=b.trend,px=D.bid||D.candles[D.candles.length-1][4];
 let h='<b>Bot tín hiệu</b>'+['D1','H4','H1'].map(k=>`<span class="xh ${b[k]>0?'gain':b[k]<0?'loss':''}">${k} ${b[k]>0?'▲':b[k]<0?'▼':'–'}</span>`).join('');
 if(L.bot_tin_hieu&&L.bot_tin_hieu.length)h+='<span class="hl ok">Nến vừa đóng có tín hiệu '+(L.bot_tin_hieu[0].side==='BUY'?'MUA':'BÁN')+'</span>';
 if(!tr)h+='<span>Ba khung lệch nhau nên bot không gọi lệnh.</span>';
 else{const cs=L.bot_cho||[];if(cs.length)h+=`<span title="Sau đó tín hiệu còn phải qua bộ lọc thân nến, độ dãn và khoảng dừng lỗ cho phép của bot.">${tr>0?'MUA':'BÁN'} khi `
   +cs.map(c=>{const m=tr>0?c.dinh:c.day;return `nến ${c.tf} đóng ${tr>0?'trên':'dưới'} <b>${f2(m)}</b> <span class="mo">(${tr>0?'đỉnh':'đáy'} ${c.gio} giờ, cách ${f2(Math.abs(px-m))})</span>`}).join(', hoặc ')+'</span>'}
 el.innerHTML=h}
// --- vị thế COT của vàng tương lai (CFTC): số chốt thứ Ba, công bố thứ Sáu; chỉ hiện ở trang vàng
var COTD=null;
function cotVe(){const el=$('#cot');if(!el)return;const c=COTD;if(!c||!c.bat||(D&&D.khac_vang)){el.hidden=true;return}el.hidden=false;
 const so=n=>n==null?'—':Math.round(n).toLocaleString('vi-VN'),dau=n=>n==null?'—':(n>0?'+':n<0?'−':'')+Math.abs(Math.round(n)).toLocaleString('vi-VN'),ng=s=>s.slice(8)+'/'+s.slice(5,7)+'/'+s.slice(0,4);
 let h='<h3>Vị thế lớn trên vàng tương lai (COT)</h3>';const t=c.tom;
 if(!t)h+='<p class="why">'+(c.loi?'Chưa tải được báo cáo từ CFTC: '+esc(c.loi)+'. Webapp tự thử lại sau vài giờ.':'Đang tải báo cáo từ cftc.gov lần đầu, mất chừng một phút…')+'</p>';
 else{if(t.tuoi_ngay>17)h+=`<p class="stale"><b>Báo cáo đã cũ ${t.tuoi_ngay} ngày.</b> CFTC chậm công bố hoặc máy không tải được bản mới${c.loi?' ('+esc(c.loi)+')':''}.</p>`;
  h+=kv('Báo cáo chốt ngày',ng(t.ngay)+' <span class="mo">('+t.tuoi_ngay+' ngày trước)</span>')
   +kv('Quỹ đầu cơ · mua ròng',dau(t.quy_rong)+' hợp đồng')
   +kv('So với tuần trước',dau(t.quy_doi)+' hợp đồng')
   +(t.hang!=null?kv('So với 3 năm qua','bằng hoặc cao hơn '+t.hang+'% số tuần'):'')
   +kv('Ngân hàng, đại lý hoán đổi · ròng',dau(t.nh_rong))
   +kv('Nhà sản xuất, bên phòng hộ · ròng',dau(t.sx_rong))
   +kv('Tổng hợp đồng đang mở',so(t.oi));
  const v=(t.chuoi||[]).map(x=>x[1]);
  if(v.length>1){const lo=Math.min(...v,0),hi=Math.max(...v,0),W=260,H=46,X=i=>(i*(W-2)/(v.length-1)+1).toFixed(1),Y=y=>(H-2-(y-lo)*(H-4)/((hi-lo)||1)).toFixed(1);
   h+=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" role="img" aria-label="Vị thế mua ròng của quỹ đầu cơ trong ${v.length} tuần gần nhất" style="display:block;margin:10px 0 2px"><line x1="0" x2="${W}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--line)" vector-effect="non-scaling-stroke"/><polyline fill="none" stroke="var(--series)" stroke-width="1.6" vector-effect="non-scaling-stroke" points="${v.map((y,i)=>X(i)+','+Y(y)).join(' ')}"/></svg><p class="why" style="margin-top:0">Mua ròng của quỹ, ${v.length} tuần gần nhất. Đường ngang là mức 0.</p>`}}
 h+='<p class="why">Số liệu chốt thứ Ba, công bố thứ Sáu, nên lúc bạn đọc đã cũ 3 tới 10 ngày. Đây là vàng tương lai ở sàn COMEX, không phải khối lượng trên sàn bạn đang giao dịch; vàng và forex giao ngay không có sàn tập trung nên không nguồn nào có khối lượng đó theo thời gian thực.</p>'
  +'<p class="why"><b>Đã đo, và nó không báo trước được giá.</b> Trên 463 tuần từ 2018 tới 11/2026, lợi suất vàng 1 tuần và 4 tuần sau khi báo cáo ra không khác nhau có ý nghĩa giữa lúc quỹ mua ròng nhiều và ít, hay giữa tuần quỹ mua thêm và bán bớt (bốn phép so, p nhỏ nhất 0,08, ngưỡng 0,0125). Trong chính tuần chốt thì quỹ mua thêm ở 72% số tuần giá tăng: vị thế đi theo giá, không đi trước giá. Khung này để biết bối cảnh, không phải tín hiệu vào lệnh.</p>';
 el.innerHTML=h}
async function cotTai(){try{const r=await fetch('/api/cot',{cache:'no-store'});if(!r.ok)throw 0;COTD=await r.json()}catch(e){return}cotVe();if(COTD&&COTD.bat&&!COTD.tom&&!COTD.loi)setTimeout(cotTai,20000)}
// nhãn lệnh đang mở ghép từ tên, chiều và số lot: 'Mua'/'Bán' là chữ của trang nên bản tiếng Anh dịch thành Buy/Sell rồi viết hoa,
// không cần khóa dịch riêng cho từng tên EA. Dữ liệu cũ chưa có 'ten' thì dùng nguyên nhãn.
function nhanL(o){return o.ten==null?o.nhan:o.ten+' '+(o.huong==='BUY'?'Mua':'Bán').toUpperCase()+(o.lot!=null?' '+String(o.lot):'')}
function side(){cotVe();const L=D.luat,S=$('#side');let h='';
 if(D.khac_vang){const b=L.bot||{};if(L.tuoi_phut>90)h+=`<p class="stale"><b>Giá cũ ${L.tuoi_phut>=120?Math.floor(L.tuoi_phut/60)+' giờ':L.tuoi_phut+' phút'}.</b> Thị trường của mã này đang nghỉ hoặc MT5 không có giá mới.</p>`;
  h+=`<h3>${esc(D.ma)}</h3><p class="why">${esc(D.ten||'')} · ${esc(D.nhom||'')}</p>`+kv('Giá Bid / Ask','<span class="sg-ba">'+fp(D.bid)+' / '+fp(D.ask)+'</span>')
   +'<h3>Xu hướng</h3>'+kv('D1 · giá so với EMA200',DIR(b.D1))+kv('H4 · EMA20 so với EMA50',DIR(b.H4))+kv('H1 · EMA20 so với EMA50',DIR(b.H1))+kv('Cả ba khung',b.trend?DIR(b.trend):'<span class="dir">LỆCH NHAU</span>')
   +'<h3>Biên độ và mức giá</h3>'+kv('ATR14 (M15)',fp(b.atr))+kv('Kháng cự 2 giờ',fp(b.resistance))+kv('Hỗ trợ 2 giờ',fp(b.support));
  h+='<p class="why" style="margin-top:10px">'+(D.chia_se?'Bản chia sẻ không có luật vào lệnh riêng của ai. Các phương pháp tùy chọn tính theo ATR, và được đo trên nến 5 phút của chính mã này lấy từ MT5 của bạn.':'Luật trong sổ của bạn không áp cho mã này. Các phương pháp tùy chọn áp được vì tính theo ATR, và được đo trên nến 5 phút của chính mã này từ đầu năm.')+'</p>';
  for(const e of L.loi||[])h+=`<p class="stale">${esc(e)}</p>`;S.innerHTML=h;$('#src').innerHTML='<span class="live"></span>giá trực tiếp từ MT5 demo · '+(ES?'theo từng tick':'5 giây một lần');return}
 if(L.tuoi_phut>90)h+=`<p class="stale"><b>Giá cũ ${L.tuoi_phut>=120?Math.floor(L.tuoi_phut/60)+' giờ':L.tuoi_phut+' phút'}.</b> ${D.nguon==='mt5'?'MT5 không có giá mới (thị trường nghỉ hoặc mất kết nối).':'Kho nến chỉ được cập nhật mỗi giờ, khi vòng chạy bóng đang chạy và thị trường mở.'} Các ô dưới đây tính trên nến cũ.</p>`;
 h+='<h3>Xu hướng</h3>';
 if(L.bot)h+=kv('D1 · giá so với EMA200',DIR(L.bot.D1))+kv('H4 · EMA20 so với EMA50',DIR(L.bot.H4))+kv('H1 · EMA20 so với EMA50',DIR(L.bot.H1))+kv('Cả ba khung',L.bot.trend?DIR(L.bot.trend):'<span class="dir">LỆCH NHAU</span>');
 h+='<h3>Luật của bot tín hiệu</h3>';
 if(L.bot_tin_hieu&&L.bot_tin_hieu.length)for(const s of L.bot_tin_hieu)h+=`<p class="verdict">${s.side==='BUY'?'MUA':'BÁN'} · ${esc(s.tf)} · kiểu ${esc(s.kind)}</p><p class="why">${esc(s.reason)} SL theo luật: ${f2(s.sl)}.</p>`;
 else h+='<p class="verdict">Không có tín hiệu ở nến vừa đóng</p><p class="why">Luật chỉ ra lệnh khi ba khung cùng chiều và nến đóng phá đỉnh hoặc đáy của quãng trước đó.</p>';
 if(L.bot)h+=kv('Kháng cự 2 giờ',f2(L.bot.resistance))+kv('Hỗ trợ 2 giờ',f2(L.bot.support))+kv('ATR14 (M15)',f2(L.bot.atr));
 h+='<h3>Luật xu hướng ba khung</h3>';
 if(L.ba_khung){const q=L.ba_khung.quyet_dinh;h+=`<p class="verdict">${q==='MUA'?'MUA':q==='BAN'?'BÁN':'Đứng ngoài'}</p><p class="why">${L.ba_khung.trong_gio?'Nến vừa đóng nằm trong khung giờ của luật.':'Nến vừa đóng nằm ngoài khung giờ của luật (14:00–03:00 giờ Việt Nam, thứ Hai tới thứ Sáu).'} Luật cần thắng trên 80% số lệnh mới hòa vốn.</p>`}
 h+='<h3>Luật đỉnh/đáy 8 giờ</h3>';
 if(L.dinh_day){const d=L.dinh_day,q=d.hanh_dong;h+=`<p class="verdict">${q==='MUA'?'MUA':q==='BAN'?'BÁN':'Đứng ngoài'}</p><p class="why">${esc(d.ly_do||'')}</p>`;if(q==='MUA'||q==='BAN')h+=kv('Giá vào',f2(d.gia_vao))+kv('SL',f2(d.sl))+kv('TP',f2(d.tp1))}
 h+='<h3>Lệnh đang mở</h3>'+((D.lenh||[]).length?D.lenh.map(o=>kv(esc(nhanL(o))+(o.loai==='demo'?' · demo':' · tín hiệu'),'vào '+f2(o.vao)+' · SL '+f2(o.sl))).join(''):'<p class="why">Bot và các EA demo không có lệnh nào đang mở.</p>');
 h+='<h3>Tin USD mạnh</h3>';
 if(L.tin){h+=L.tin.dang_ne?'<p class="verdict">Đang trong giờ né tin</p>':'';h+=(L.tin.sap_toi.length?L.tin.sap_toi.map(t=>kv('Sắp tới',vn(Date.parse(t)/1000))).join(''):'<p class="why">Không còn tin nào trong lịch.</p>')+kv('Lịch phủ tới',L.tin.phu_toi?vn(Date.parse(L.tin.phu_toi)/1000,1):'—')}
 h+='<h3>Dữ liệu</h3>'+kv('Nguồn giá',D.nguon==='mt5'?'MT5 demo, trực tiếp':'kho nến 1 phút')+(D.nguon==='mt5'&&D.bid?kv('Bid / Ask','<span class="sg-ba">'+fp(D.bid)+' / '+fp(D.ask)+'</span>'):'')+kv('Giá mới nhất lúc','<span class="sg-luc">'+vn(Date.parse(L.het)/1000)+'</span>');
 if(D.nguon!=='mt5'&&D.ly_do_khong_song)h+=`<p class="why">Chưa dùng giá trực tiếp: ${esc(D.ly_do_khong_song)}.</p>`;
 $('#src').innerHTML=D.nguon==='mt5'?'<i class="live"></i>giá trực tiếp từ MT5 demo · '+(ES?'theo từng tick':'5 giây một lần'):'<i class="live off"></i>kho nến 1 phút · cập nhật mỗi giờ';
 for(const e of L.loi||[])h+=`<p class="stale">${esc(e)}</p>`;S.innerHTML=h}
// --- nến lùi về đầu năm: nạp một lần cho mỗi mã và khung, rồi ghép vào trước 900 nến đang chạy
const HISM=new Map(),IND=['ema20','ema50','bb_tren','bb_duoi','rsi','ho_tro','khang_cu'],hisKhoa=()=>(ma||'XAU')+'|'+tf;let hisDang='',hisLoi='';
function hisChu(j){const el=$('#his');if(!el)return;el.textContent=!j?'':typeof j==='string'?' '+j:j.tu?` Nến ${tf} có từ ${new Date(j.tu).toLocaleDateString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})} (${j.so_nen.toLocaleString('vi-VN')} nến)${j.cat_bot?'; khung này quá nhiều nến nên không lùi được tới đầu năm, hãy chọn khung lớn hơn':''}.`:''}
function hisGhep(){const h=HISM.get(hisKhoa());if(!h||!D||!D.candles.length)return;const t0=D.candles[0][0],hc=h.candles;let a=0,b=hc.length;while(a<b){const m=(a+b)>>1;if(hc[m][0]<t0)a=m+1;else b=m}
 if(!a)return;D.candles=hc.slice(0,a).concat(D.candles);for(const k of IND)if(D[k])D[k]=(h[k]?h[k].slice(0,a):new Array(a).fill(null)).concat(D[k]);if(D.live>=0)D.live+=a;CBS=null}
async function hisTai(){const key=hisKhoa();if(HISM.has(key)){hisChu(HISM.get(key));return}if(hisDang===key||hisLoi===key)return;hisDang=key;hisChu('Đang nạp nến từ đầu năm…');
 try{const r=await fetch('/api/gia-cu?tf='+tf+(ma?'&ma='+encodeURIComponent(ma):''),{cache:'no-store'});if(!r.ok)throw new Error(await r.text());const j=await r.json();
  HISM.set(key,j);while(HISM.size>3)HISM.delete(HISM.keys().next().value);if(key===hisKhoa()){hisChu(j);hisGhep();draw()}}
 catch(e){hisLoi=key;if(key===hisKhoa())hisChu('Chưa nạp được nến cũ: '+e.message)}hisDang=''}
// --- luồng giá trực tiếp: máy chủ đẩy từng tick của MT5 về ngay (Server-Sent Events), trang chỉ vẽ lại cây nến đang chạy và đường Bid/Ask.
// Cả biểu đồ (chỉ báo, luật) vẫn tải lại định kỳ và ngay sau khi một nến đóng.
let ES=null,esKhoa='',SG=null,sgVe=0,sgNap=0,CBS=null,LECH=null,sgBen=0;
const TFS={M5:300,M15:900,M30:1800,H1:3600,H4:14400,D1:86400};
const sgK=()=>(ma||'')+'|'+tf;
function sgDong(){if(ES){ES.close();ES=null}esKhoa=''}
function sgMo(){if(!D||D.nguon!=='mt5'||document.visibilityState!=='visible'||!window.EventSource){sgDong();return}const k=sgK();if(ES&&esKhoa===k)return;
 sgDong();esKhoa=k;SG=null;LECH=null;ES=new EventSource('/api/song?tf='+tf+(ma?'&ma='+encodeURIComponent(ma):''));ES.onerror=()=>{esLoi=1;srcVe()};
 ES.onmessage=e=>{let x;try{x=JSON.parse(e.data)}catch(er){return}if(esKhoa!==k)return;x.k=k;SG=x;esLoi=0;const l=x.ms-Date.now();if(Math.abs(l)<60000)LECH=LECH==null?l:Math.max(l,LECH-5);if(sgAp(x))sgHen()}}
// hẹn vẽ: khung hình kế tiếp, hoặc sau 100 ms nếu trình duyệt đang hãm requestAnimationFrame (cửa sổ bị che, tab nền)
function sgHen(){if(sgVe)return;sgVe=1;const f=()=>{if(sgVe)sgKe()};requestAnimationFrame(f);setTimeout(f,100)}
// áp một tick vào D: cập nhật nến đang chạy, hoặc thêm nến mới khi MT5 đã mở nến kế tiếp
function sgAp(x){if(!x||x.k!==sgK()||!D||D.nguon!=='mt5'||!D.candles.length)return false;D.bid=x.bid;D.ask=x.ask;const k=x.nen,cs=D.candles;if(!k)return true;
 const last=cs[cs.length-1];if(k[0]===last[0]){last[1]=k[1];last[2]=k[2];last[3]=k[3];last[4]=k[4];D.live=cs.length-1}
 else if(k[0]>last[0]){cs.push(k.slice());for(const n of IND)if(D[n])D[n].push(null);D.live=cs.length-1;if(LW)LW.idx.set(k[0],cs.length-1);
  clearTimeout(sgNap);sgNap=setTimeout(()=>load(1),4500)}                     // nến vừa đóng: tải lại để chỉ báo và luật tính trên nến mới đóng
 cbSong();return true}
// chỉ báo của cây nến đang chạy, tính tiếp từ nến đã đóng theo đúng công thức của máy chủ (gia.py): EMA kiểu ewm adjust=False,
// Bollinger 20 nến độ lệch chuẩn tổng thể (ddof=0) nhân 2, RSI14 kiểu Wilder. Nến đã đóng giữ nguyên số máy chủ gửi.
function cbDung(){CBS=null;if(!D)return;const cs=D.candles,n=D.live>=0?D.live:cs.length;if(n<2)return;let up=null,dn=null;
 for(let j=1;j<n;j++){const d=cs[j][4]-cs[j-1][4],u=d>0?d:0,v=d<0?-d:0;if(up==null){up=u;dn=v}else{up+=(u-up)/14;dn+=(v-dn)/14}}
 CBS={i:n-1,e20:D.ema20?D.ema20[n-1]:null,e50:D.ema50?D.ema50[n-1]:null,up,dn}}
function cbTien(j){const cs=D.candles,c=cs[j][4],d=c-cs[j-1][4];CBS.up+=((d>0?d:0)-CBS.up)/14;CBS.dn+=((d<0?-d:0)-CBS.dn)/14;
 if(CBS.e20!=null)CBS.e20+=2/21*(c-CBS.e20);if(CBS.e50!=null)CBS.e50+=2/51*(c-CBS.e50);CBS.i=j}
function cbSong(){if(!D||D.live<1)return;const cs=D.candles,i=D.live;if(!CBS||CBS.i>i-1)cbDung();if(!CBS)return;while(CBS.i<i-1)cbTien(CBS.i+1);const c=cs[i][4];
 if(D.ema20&&CBS.e20!=null)D.ema20[i]=CBS.e20+2/21*(c-CBS.e20);
 if(D.ema50&&CBS.e50!=null)D.ema50[i]=CBS.e50+2/51*(c-CBS.e50);
 if(D.bb_tren&&D.bb_duoi&&i>=19){let m=0;for(let j=i-19;j<=i;j++)m+=cs[j][4];m/=20;let q=0;for(let j=i-19;j<=i;j++)q+=(cs[j][4]-m)**2;const sd=Math.sqrt(q/20);D.bb_tren[i]=m+2*sd;D.bb_duoi[i]=m-2*sd}
 if(D.rsi&&CBS.up!=null&&i>=15){const d=c-cs[i-1][4],u=CBS.up+((d>0?d:0)-CBS.up)/14,v=CBS.dn+((d<0?-d:0)-CBS.dn)/14;D.rsi[i]=v===0?100:100-100/(1+u/v)}}
// đồng hồ đếm ngược tới lúc nến đóng, hiện cạnh giá trên trục giá; tính theo giờ của sàn (giờ tick), không theo giờ máy
function demVe(){if(!LW)return;let t='';
 if(D&&D.live>=0&&D.nguon==='mt5'&&ES&&TFS[tf]){const con=Math.floor(D.candles[D.live][0]+TFS[tf]-(Date.now()+(LECH||0))/1000);
  if(con>=0&&con<=TFS[tf]){const h=Math.floor(con/3600),m=Math.floor(con%3600/60),s=con%60,p=v=>String(v).padStart(2,'0');t=(h?h+':'+p(m):p(m))+':'+p(s)}}
 if(t!==LW.dem){LW.dem=t;LW.nen.applyOptions({title:t})}}
setInterval(demVe,250);
// dòng nguồn giá nói đúng tình trạng: đang chạy theo tick, mất kết nối luồng (đang nối lại), hay thị trường đang nghỉ (không có tick mới quá 2 phút)
let esLoi=0;
function srcVe(){const sr=$('#src');if(!sr||!D||D.nguon!=='mt5'||!ES)return;let h;
 if(esLoi)h='<i class="live off"></i>mất kết nối luồng giá, đang nối lại…';
 else if(SG&&SG.ms&&Date.now()-SG.ms>120000)h='<i class="live off"></i>thị trường đang nghỉ · giá cuối lúc '+new Date(SG.ms).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
 else h='<i class="live"></i>giá trực tiếp từ MT5 demo · theo từng tick';
 if(sr.innerHTML!==h)sr.innerHTML=h}
setInterval(srcVe,1000);
function sgKe(){sgVe=0;if(!D||!D.candles.length)return;const cs=D.candles,i=cs.length-1,k=cs[i];
 if(LW){const P=pal(),mo=h=>h.length===7?h+'99':h,u=k[4]>=k[1];
  const duong=j=>{const t=cs[j][0];for(const[s,a,b]of[[LW.e20,D.ema20,on.ema20],[LW.e50,D.ema50,on.ema50],[LW.bbt,D.bb_tren,on.bb],[LW.bbd,D.bb_duoi,on.bb],[LW.rsi,D.rsi,on.rsi]])
   if(s&&b&&a&&a[j]!=null)try{s.update({time:t,value:a[j]})}catch(e){}};
  if(LW.tCuoi!=null&&k[0]>LW.tCuoi){for(let j=LW.idx.get(LW.tCuoi);j!=null&&j<i;j++){const q=cs[j];LW.nen.update({time:q[0],open:q[1],high:q[2],low:q[3],close:q[4]});duong(j)}}
  if(LW.tCuoi==null||k[0]>=LW.tCuoi){LW.nen.update({time:k[0],open:k[1],high:k[2],low:k[3],close:k[4],color:mo(u?P.bull:P.bear),wickColor:mo(u?P.wick:P.wickDn),borderColor:mo(u?P.wick:P.wickDn)});duong(i);LW.tCuoi=k[0]}
  if(LW.askL&&D.ask)LW.askL.applyOptions({price:D.ask});if(!LW.hov)lwDoc(null);lwPhu();demVe()}
 else draw();
 plCach();
 for(const e of document.querySelectorAll('.sg-ba'))e.textContent=fp(D.bid)+' / '+fp(D.ask);
 if(SG&&SG.ms){const l=new Date(SG.ms).toLocaleTimeString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit'});for(const e of document.querySelectorAll('.sg-luc'))e.textContent=l}
 srcVe();
 const bay=performance.now();if(bay-sgBen>500){sgBen=bay;botTT()}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'){if(D)load(1)}else sgDong()});
async function load(keep){try{const r=await fetch('/api/gia?tf='+tf+'&n=900'+(ma?'&ma='+encodeURIComponent(ma):''),{cache:'no-store'});if(!r.ok)throw new Error(await r.text());D=await r.json();D.live=-1;dg=D.so_le==null?2:D.so_le;document.body.toggleAttribute('data-khac',!!D.khac_vang);$('#tieu-de').textContent=D.khac_vang&&!D.chia_se?'Biểu đồ '+D.ma:'Biểu đồ vàng';{const cn=$('#chan-nguon');if(cn&&D.chia_se)cn.textContent='Giá và nến đọc trực tiếp từ MT5 của bạn ở chế độ chỉ đọc. Trang không tự mở MT5 và không có lệnh đặt lệnh nào. Chỉ báo tính trên nến đã đóng; các phương pháp tùy chọn tính theo ATR. '}{const dt=$('#doc-truoc');if(dt&&D.chia_se)dt.innerHTML='<b>Đọc trước:</b> giá và nến lấy trực tiếp từ MT5 của bạn. Các phương án ở nút Phân tích điểm vào là những phương pháp tùy chọn tính theo ATR, kèm kết quả đo lại trên dữ liệu quá khứ của chính mã đó; kết quả quá khứ không bảo đảm tương lai. Trang này không đặt lệnh và không phải lời khuyên đầu tư.'}$('#ma-nhan').textContent=D.khac_vang?D.ma+(D.chia_se?' · bản chia sẻ, phương pháp tùy chọn tính theo ATR':' · phương pháp tùy chọn, đo trên dữ liệu của chính mã'):'XAUUSD · luật tính trên nến đã đóng';
  hisGhep();plCach();if(D.dang_chay){D.candles.push(D.dang_chay);for(const k of['ema20','ema50','bb_tren','bb_duoi','ho_tro','khang_cu','rsi'])if(D[k])D[k].push(null);D.live=D.candles.length-1}
  CBS=null;if(SG&&SG.k===sgK())sgAp(SG);else cbSong();                                                  // tick mới nhất của luồng luôn mới hơn bản vừa tải
  if(!keep)view={n:defN(),off:0};draw();side();botTT();rkAtr();zNow();sgMo();srcVe();$('#err').textContent='';delete $('.stage').dataset.tai;hisTai();tkTai()}catch(e){$('#err').textContent='Không tải được dữ liệu: '+e.message;delete $('.stage').dataset.tai}}
const luu=()=>{try{localStorage.setItem('so-on2',JSON.stringify(on));localStorage.setItem('so-kieu3',kieu)}catch(e){}};
document.querySelectorAll('.seg.tf button').forEach(b=>b.addEventListener('click',()=>{tf=b.dataset.tf;document.querySelectorAll('.seg.tf button').forEach(o=>o.setAttribute('aria-pressed',o===b));load()}));
document.querySelectorAll('.seg.kieu button').forEach(b=>{b.setAttribute('aria-pressed',b.dataset.kieu===kieu);b.addEventListener('click',()=>{kieu=b.dataset.kieu;document.querySelectorAll('.seg.kieu button').forEach(o=>o.setAttribute('aria-pressed',o===b));luu();draw()})});
document.querySelectorAll('.chip[data-k]').forEach(b=>{const k=b.dataset.k;b.setAttribute('aria-pressed',!!on[k]);b.addEventListener('click',()=>{on[k]=on[k]?0:1;luu();boVe();draw()})});
const boVe=()=>{document.querySelectorAll('.chip[data-k]').forEach(b=>b.setAttribute('aria-pressed',!!on[b.dataset.k]));$('#so-cb').textContent=Object.keys(BO.gon).filter(k=>on[k]).length+'/'+Object.keys(BO.gon).length;document.querySelectorAll('.seg.bo button').forEach(b=>b.setAttribute('aria-pressed',Object.keys(BO.gon).every(k=>!!on[k]===!!BO[b.dataset.bo][k])))};
document.querySelectorAll('.seg.bo button').forEach(b=>b.addEventListener('click',()=>{Object.assign(on,BO[b.dataset.bo]);luu();boVe();draw()}));boVe();
document.addEventListener('click',e=>{const d=$('details.tuy');if(d.open&&!d.contains(e.target))d.open=false});
// bảng chọn chỉ báo: dời sang trái cho vừa màn hình hẹp (luôn cách hai mép ít nhất 12 px)
{const d=$('details.tuy'),pp=d&&d.querySelector('.chips.pop');const vua=()=>{if(!pp)return;pp.style.left='0px';const r=pp.getBoundingClientRect(),o=d.getBoundingClientRect();if(!r.width)return;const mx=document.documentElement.clientWidth-12;if(r.right>mx)pp.style.left=Math.max(12-o.left,mx-r.right)+'px'};if(pp){d.addEventListener('toggle',vua);addEventListener('resize',vua);requestAnimationFrame(vua)}}
// --- chọn mã: các mã đang hiện trong Market Watch của MT5
const MA=$('#ma');fetch('/api/ma',{cache:'no-store'}).then(r=>r.json()).then(j=>{if(!j.san_sang||!j.ds.length)return;const nh={};for(const s of j.ds)(nh[s.nhom]=nh[s.nhom]||[]).push(s);
 MA.innerHTML=Object.keys(nh).map(n=>`<optgroup label="${esc(n)}">`+nh[n].map(s=>`<option value="${s.la_vang?'':esc(s.ma)}">${esc(s.ma)} · ${esc(s.ten)}</option>`).join('')+'</optgroup>').join('');
 MA.value=[...MA.options].some(o=>o.value===ma)?ma:''}).catch(()=>{});
MA.addEventListener('change',()=>{ma=MA.value;try{localStorage.setItem('so-ma',ma)}catch(e){}plan=null;PTR=null;kcHien=null;HOC=null;nkH='';clearTimeout(hocCho);$('#pt').hidden=true;DV=[];dvVe();veDoc();veTb();history.replaceState(null,'',ma?'?ma='+encodeURIComponent(ma):location.pathname);$('.stage').dataset.tai=1;load()});
const pos=e=>{const r=C.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}};
C.addEventListener('pointermove',e=>{mouse=pos(e);if(drag&&D){const bw=(C.clientWidth-70)/view.n;view.off=drag.off+Math.round((mouse.x-drag.x)/bw)}draw()});
C.addEventListener('pointerdown',e=>{mouse=pos(e);drag={x:mouse.x,off:view.off};try{C.setPointerCapture(e.pointerId)}catch(_){}});
const tha=()=>{drag=null};C.addEventListener('pointerup',tha);C.addEventListener('pointercancel',tha);C.addEventListener('pointerleave',()=>{if(!drag){mouse=null;draw()}});
C.addEventListener('wheel',e=>{if(!D)return;e.preventDefault();view.n=Math.round(view.n*(e.deltaY>0?1.15:.87));draw()},{passive:false});
C.addEventListener('dblclick',()=>{view={n:defN(),off:0};draw()});
addEventListener('resize',fit);new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
// --- nút phóng to, thu nhỏ, về hiện tại và phím tắt
const zNow=()=>{$('#z-now').disabled=LW?false:(!view.off&&view.n===defN())},zoom=f=>{if(!D)return;if(LW){lwZoom(f);return}view.n=Math.max(20,Math.round(view.n*f));draw();zNow()},veNay=()=>{if(LW){lwNay();return}view={n:defN(),off:0};draw();zNow()};
$('#z-in').addEventListener('click',()=>zoom(.8));$('#z-out').addEventListener('click',()=>zoom(1.25));$('#z-now').addEventListener('click',veNay);
for(const ev of['pointerup','wheel','dblclick'])C.addEventListener(ev,()=>setTimeout(zNow,0));
addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey||/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName||''))return;const k=e.key;
 if(k>='1'&&k<='6'){const b=document.querySelectorAll('.seg.tf button')[+k-1];if(b)b.click()}
 else if(k==='+'||k==='=')zoom(.8);else if(k==='-'||k==='_')zoom(1.25);else if(k==='0'||k==='Home')veNay();
 else if(k==='ArrowLeft'){if(LW)lwCuon(-10);else{view.off+=10;draw();zNow()}}else if(k==='ArrowRight'){if(LW)lwCuon(10);else{view.off=Math.max(0,view.off-10);draw();zNow()}}
 else if(k==='a'||k==='A')$('#pt-btn').click();else if(k==='f'||k==='F')$('#fs-btn').click();else if((k==='h'||k==='H')&&CP.classList.contains('max'))$('#gon-btn').click();else return;e.preventDefault()});
// --- tính khối lượng lệnh
const rk={von:200,rr:1,sl:20};try{Object.assign(rk,JSON.parse(localStorage.getItem('so-rk')||'{}'))}catch(e){}
function rkDraw(){const risk=rk.von*rk.rr/100,lot=rk.sl>0?Math.floor(risk/(rk.sl*100)*100+1e-9)/100:0,min=rk.sl;let h=kv('Rủi ro cho phép',f2(risk)+' USD');
 if(!(rk.von>0&&rk.rr>0&&rk.sl>0))h='<p class="why">Nhập đủ ba ô để tính.</p>';
 else if(lot>=.01)h+=kv('Khối lượng theo mức rủi ro',f2(lot)+' lot')+kv('Lỗ nếu chạm SL',f2(lot*100*rk.sl)+' USD ('+f2(lot*100*rk.sl/rk.von*100)+'% vốn)');
 else h+=`<p class="stale"><b>Vốn này không đủ cho 0,01 lot trong mức rủi ro đã chọn.</b> 0,01 lot với SL ${f2(rk.sl)} giá sẽ lỗ ${f2(min)} USD nếu chạm SL, tức ${f2(min/rk.von*100)}% vốn.</p>`
  +kv('Vốn tối thiểu cho 0,01 lot ở mức rủi ro này',f2(min/(rk.rr/100))+' USD');
 $('#rko').innerHTML=h}
function rkAtr(){const a=D&&D.luat&&D.luat.bot&&D.luat.bot.atr;$('#rk-atr').disabled=!a;$('#rk-atr').dataset.sl=a?Math.round(a*1.5*10)/10:''}
const rkLuu=()=>{try{localStorage.setItem('so-rk',JSON.stringify(rk))}catch(e){}};
for(const k of['von','rr','sl']){const el=$('#rk-'+k);el.value=rk[k];el.addEventListener('input',()=>{rk[k]=parseFloat(el.value)||0;rkLuu();rkDraw()})}
$('#rk-atr').addEventListener('click',()=>{const v=parseFloat($('#rk-atr').dataset.sl);if(v){rk.sl=v;$('#rk-sl').value=v;rkLuu();rkDraw()}});rkDraw();
// --- công cụ vẽ: hình lưu theo từng mã ngay trong trình duyệt (theo giờ và giá) nên giữ nguyên khi đổi khung, phóng to hay tải lại trang
const VE={ds:[],cong:'tro',chon:null,tam:null,keo:null,an:false,do:null,hit:[],mau:'',cu:[],goc:null},MAUS=['','#e5532d','#17935b','#d99a00','#6250d6','#1b1f24'],veKhoa=()=>'so-ve:'+(ma||'XAU'),FIBS=[0,.236,.382,.5,.618,.786,1],
 veLuu=kh=>{const moi=JSON.stringify(VE.ds);if(!kh&&VE.goc!=null&&VE.goc!==moi){VE.cu.push(VE.goc);if(VE.cu.length>40)VE.cu.shift()}VE.goc=moi;try{localStorage.setItem(veKhoa(),moi)}catch(e){}},      // mỗi lần lưu giữ lại bản trước để hoàn tác
 veDoc=()=>{try{VE.ds=JSON.parse(localStorage.getItem(veKhoa())||'[]')}catch(e){VE.ds=[]}VE.chon=VE.tam=VE.keo=VE.do=null;VE.cu=[];VE.goc=JSON.stringify(VE.ds)},
 VEC={tro:['Chọn và di chuyển hình','M4 3l10 6.2-4.6 1.2L8 15z',''],xu:['Đoạn thẳng, đường xu hướng','M3 14.5L15 3.5M3 14.5m-1.6 0a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0-3.2 0M15 3.5m-1.6 0a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0-3.2 0','Kéo từ điểm đầu tới điểm cuối'],
  mt:['Mũi tên','M3 15L15 3M8.5 3H15v6.5','Kéo từ gốc tới đầu mũi tên'],tia:['Tia kéo dài','M3 14.5L16 5M3 14.5m-1.6 0a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0-3.2 0M9.5 9.7m-1.3 0a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0-2.6 0','Kéo từ điểm gốc qua điểm thứ hai; tia tự kéo dài tới mép biểu đồ'],
  ngang:['Đường ngang','M2 9h14M9 9m-1.7 0a1.7 1.7 0 1 0 3.4 0a1.7 1.7 0 1 0-3.4 0','Bấm vào mức giá cần đánh dấu'],doc:['Đường dọc','M9 2v14M9 9m-1.7 0a1.7 1.7 0 1 0 3.4 0a1.7 1.7 0 1 0-3.4 0','Bấm vào thời điểm cần đánh dấu'],
  kenh:['Kênh song song','M2 11.5L13 2.5M5 15.5L16 6.5','Kéo đường thứ nhất; đường song song kéo chỉnh bằng chấm ở giữa'],hop:['Vùng chữ nhật','M3 5h12v8H3z','Kéo từ một góc tới góc đối diện'],
  elip:['Hình elip','M9 9m-6.5 0a6.5 4.3 0 1 0 13 0a6.5 4.3 0 1 0-13 0','Kéo từ một góc tới góc đối diện'],fib:['Fibonacci thoái lui','M2 4h14M2 9h14M2 14h14M4 14L14 4','Kéo từ điểm bắt đầu nhịp tới điểm kết thúc nhịp'],
  vt:['Vị thế: điểm vào, dừng lỗ, chốt lời','M3 3h12v6H3zM3 9h12v6H3z','Kéo từ điểm vào tới điểm dừng lỗ: kéo xuống là MUA, kéo lên là BÁN'],do:['Thước đo giá và thời gian','M3 12l9-9 3 3-9 9zM6.5 10.5l1 1M8.5 8.5l1 1M10.5 6.5l1 1','Kéo để đo; bấm chỗ khác để bỏ'],
  but:['Bút vẽ tự do','M3 14c2-5 3 2 5-3s3 1 4-3 2-3 3-4','Giữ chuột và vẽ'],chu:['Ghi chú','M4 4h10M9 4v10M7 14h4','Bấm vào chỗ cần ghi chú rồi gõ chữ']},
 VEL={mau:['Màu nét vẽ: bấm để đổi (áp cho hình đang chọn và hình vẽ sau)','M9 9m-5.5 0a5.5 5.5 0 1 0 11 0a5.5 5.5 0 1 0-11 0'],hoan:['Hoàn tác (Ctrl+Z)','M6 7h5.5a3.5 3.5 0 0 1 0 7H7M6 7l3-3M6 7l3 3'],
  an:['Ẩn hoặc hiện các hình đã vẽ','M2 9s2.8-5 7-5 7 5 7 5-2.8 5-7 5-7-5-7-5zM9 9m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0'],xoa:['Xóa hình đang chọn (phím Delete)','M4 6h10M7 6V4h4v2M5.5 6l.7 9h5.6l.7-9'],het:['Xóa tất cả hình của mã này','M3 5h12M6.5 5V3h5v2M5 5l.6 10h6.8L13 5M7.5 8l3 4M10.5 8l-3 4']};
const VTB=document.createElement('div'),VGOI=document.createElement('div');VTB.className='vetb';VTB.setAttribute('role','toolbar');VTB.setAttribute('aria-label','Công cụ vẽ');VGOI.className='vegoi';VGOI.hidden=true;
function veHoan(){if(!VE.cu.length)return;try{VE.ds=JSON.parse(VE.cu.pop())}catch(e){return}VE.chon=null;veLuu(1);veTb();lwPhu()}
function veTb(){const tat=k=>(k==='xoa'&&!VE.chon)||(k==='het'&&!VE.ds.length)||(k==='hoan'&&!VE.cu.length),mau=VE.mau||css('--series')||'#2f6fed',
  nut=(k,[ten,d],kieu)=>`<button type="button" data-${kieu}="${k}" title="${ten}" aria-label="${ten}"${kieu==='c'?` aria-pressed="${VE.cong===k}"`:k==='an'?` aria-pressed="${VE.an}"`:''}${tat(k)?' disabled':''}><svg viewBox="0 0 18 18" width="18" height="18" fill="${k==='mau'?mau:'none'}" stroke="${k==='mau'?mau:'currentColor'}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg></button>`;
 VTB.innerHTML='<button type="button" class="mo" title="Mở hoặc thu gọn công cụ vẽ" aria-label="Mở hoặc thu gọn công cụ vẽ"><svg viewBox="0 0 18 18" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 15l1-4 8-8 3 3-8 8zM11 4l3 3"/></svg></button>'+Object.entries(VEC).map(([k,v])=>nut(k,v,'c')).join('')+'<i></i>'+Object.entries(VEL).map(([k,v])=>nut(k,v,'l')).join('');
 VTB.querySelector('.mo').addEventListener('click',()=>VTB.toggleAttribute('data-thu'));
 VTB.querySelectorAll('[data-c]').forEach(b=>b.addEventListener('click',()=>veCong(b.dataset.c)));
 VTB.querySelectorAll('[data-l]').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.l;if(k==='an')VE.an=!VE.an;else if(k==='xoa')veXoa();else if(k==='hoan')veHoan();
   else if(k==='mau'){VE.mau=MAUS[(MAUS.indexOf(VE.mau)+1)%MAUS.length];const h=VE.ds.find(x=>x.id===VE.chon);if(h){if(VE.mau)h.mau=VE.mau;else delete h.mau;veLuu()}}
   else if(VE.ds.length&&confirm('Xóa tất cả '+VE.ds.length+' hình đã vẽ trên '+(ma||'XAUUSD')+'? Bấm Hoàn tác nếu đổi ý.')){VE.ds=[];VE.chon=null;veLuu()}veTb();lwPhu()}));
 VGOI.textContent=VE.cong==='tro'?'':VEC[VE.cong][2]+' · Esc để thôi';VGOI.hidden=VE.cong==='tro'}
function veCong(c){VE.cong=c;VE.tam=VE.keo=null;if(c!=='tro'){VE.an=false;VE.chon=null}document.body.toggleAttribute('data-ve',c!=='tro');veTb();lwPhu()}
function veXoa(){if(!VE.chon)return;VE.ds=VE.ds.filter(h=>h.id!==VE.chon);VE.chon=null;veLuu();veTb();lwPhu()}
function veToa(px,py){if(!LW||!D)return null;const cs=D.candles,n=cs.length,dt=n>1?cs[1][0]-cs[0][0]:900,l=LW.chart.timeScale().coordinateToLogical(px),g=LW.nen.coordinateToPrice(py);if(l==null||g==null)return null;
 const i=Math.round(l);return{t:i<0?cs[0][0]+i*dt:i>=n?cs[n-1][0]+(i-n+1)*dt:cs[i][0],p:g}}
// vẽ mọi hình lên lớp phủ và ghi lại hình dạng trên màn hình của từng hình để bắt chuột
function veVe(X,o){const{y,pw,ph,P,cs,dt,ts}=o,n=cs.length;VE.hit=[];
 const ix=t=>{if(t<=cs[0][0])return(t-cs[0][0])/dt;if(t>=cs[n-1][0])return n-1+(t-cs[n-1][0])/dt;let a=0,b=n-1;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}return a},vx=t=>ts.logicalToCoordinate(ix(t));
 X.font='11px Tahoma,"Segoe UI",Arial,sans-serif';X.textBaseline='alphabetic';X.setLineDash([]);
 const chu=(t,x,yy,col,phai)=>{const w=X.measureText(t).width,x0=Math.max(4,Math.min(phai?x-w:x,pw-w-6));X.globalAlpha=.88;X.fillStyle=P.bg;X.fillRect(x0-3,yy-11,w+6,14);X.globalAlpha=1;X.fillStyle=col;X.textAlign='left';X.fillText(t,x0,yy);return w},
  cham=(x,yy,col)=>{X.fillStyle=P.bg;X.strokeStyle=col;X.lineWidth=1.6;X.beginPath();X.arc(x,yy,4.5,0,7);X.fill();X.stroke()},
  doan=(x1,y1,x2,y2,x,yy)=>{const dx=x2-x1,dy=y2-y1,L=dx*dx+dy*dy||1,k=Math.max(0,Math.min(1,((x-x1)*dx+(yy-y1)*dy)/L));return Math.hypot(x-x1-k*dx,yy-y1-k*dy)},
  tg=s=>{s=Math.abs(s);return s>=172800?f2(s/86400)+' ngày':s>=7200?f2(s/3600)+' giờ':Math.round(s/60)+' phút'},atr=PTR&&PTR.boi_canh&&PTR.boi_canh.atr_m15;
 if(VE.do){const a=VE.do.a,b=VE.do.b,xa=vx(a.t),xb=vx(b.t),ya=y(a.p),yb=y(b.p);if(xa!=null&&xb!=null&&ya!=null&&yb!=null){const len=b.p>=a.p,col=len?P.tp:P.sl;X.globalAlpha=.13;X.fillStyle=col;X.fillRect(Math.min(xa,xb),Math.min(ya,yb),Math.abs(xb-xa),Math.abs(yb-ya));X.globalAlpha=1;
   X.strokeStyle=col;X.lineWidth=1;X.strokeRect(Math.min(xa,xb)+.5,Math.min(ya,yb)+.5,Math.abs(xb-xa),Math.abs(yb-ya));
   chu((len?'+':'−')+fp(Math.abs(b.p-a.p))+' ('+(len?'+':'−')+f2(Math.abs(b.p/a.p-1)*100)+'%)'+(atr?' · '+f2(Math.abs(b.p-a.p)/atr)+' ATR':'')+' · '+Math.round(Math.abs(b.t-a.t)/dt)+' nến · '+tg(b.t-a.t),Math.min(xa,xb)+4,(len?Math.min(ya,yb)-5:Math.max(ya,yb)+14),col)}}
 if(VE.an&&!VE.tam)return;
 for(const h of VE.tam?[...VE.ds,VE.tam]:VE.ds){const sel=h.id===VE.chon,col=h.mau||P.vao,xa=vx(h.a.t),ya=y(h.a.p),xb=h.b?vx(h.b.t):null,yb=h.b?y(h.b.p):null;if(xa==null||ya==null||(h.b&&(xb==null||yb==null)))continue;let g=null;X.lineWidth=sel?2.2:1.5;X.strokeStyle=col;
  if(h.k==='xu'){X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.stroke();g={nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>doan(xa,ya,xb,yb,x,yy)<=6}}
  else if(h.k==='ngang'){const Y=Math.round(ya)+.5;X.beginPath();X.moveTo(0,Y);X.lineTo(pw,Y);X.stroke();chu(fp(h.a.p),pw-6,Y-4,col,1);g={nut:[],trong:(x,yy)=>Math.abs(yy-Y)<=5}}
  else if(h.k==='hop'){const x0=Math.min(xa,xb),y0=Math.min(ya,yb),w=Math.abs(xb-xa),hh=Math.abs(yb-ya);X.globalAlpha=.1;X.fillStyle=col;X.fillRect(x0,y0,w,hh);X.globalAlpha=1;X.strokeRect(x0+.5,y0+.5,w,hh);
   chu(fp(Math.max(h.a.p,h.b.p))+' – '+fp(Math.min(h.a.p,h.b.p)),x0+4,y0-4,col);g={nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>x>=x0-3&&x<=x0+w+3&&yy>=y0-3&&yy<=y0+hh+3}}
  else if(h.k==='fib'){const x0=Math.min(xa,xb);X.lineWidth=1;X.strokeStyle=P.mute;X.setLineDash([4,3]);X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.stroke();X.setLineDash([]);
   for(const f of FIBS){const gia=h.b.p-(h.b.p-h.a.p)*f,Y=Math.round(y(gia))+.5,dam=f===.5||f===.618;X.strokeStyle=dam?col:P.mute;X.lineWidth=dam?1.4:1;X.beginPath();X.moveTo(x0,Y);X.lineTo(pw,Y);X.stroke();chu(f2(f*100).replace(',00','')+'% · '+fp(gia),x0+4,Y-3,dam?col:P.mute)}
   g={nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>x>=x0-3&&yy>=Math.min(ya,yb)-4&&yy<=Math.max(ya,yb)+4}}
  else if(h.k==='vt'){const x0=Math.min(xa,xb),x1=Math.max(Math.max(xa,xb),x0+70),ysl=y(h.sl),ytp=y(h.tp),len=h.sl<h.a.p,rr=Math.abs(h.a.p-h.sl),ld=Math.abs(h.tp-h.a.p);if(ysl==null||ytp==null)continue;
   X.globalAlpha=.14;X.fillStyle=P.sl;X.fillRect(x0,Math.min(ya,ysl),x1-x0,Math.abs(ysl-ya));X.fillStyle=P.tp;X.fillRect(x0,Math.min(ya,ytp),x1-x0,Math.abs(ytp-ya));X.globalAlpha=1;
   X.strokeStyle=P.vao;X.lineWidth=sel?2:1.4;X.beginPath();X.moveTo(x0,Math.round(ya)+.5);X.lineTo(x1,Math.round(ya)+.5);X.stroke();
   chu((len?'MUA ':'BÁN ')+fp(h.a.p)+(rr?' · R:R 1:'+f2(ld/rr):''),x0+4,ya+(len?-5:14),P.vao);chu('Dừng lỗ '+fp(h.sl)+' · −'+fp(rr)+(atr?' · '+f2(rr/atr)+' ATR':''),x0+4,(ya+ysl)/2+4,P.sl);chu('Chốt lời '+fp(h.tp)+' · +'+fp(ld),x0+4,(ya+ytp)/2+4,P.tp);
   if(!D.khac_vang&&rr&&rk.von>0&&rk.rr>0){const lot=Math.floor(rk.von*rk.rr/100/rr+1e-9)*.01;chu('0,01 lot: lỗ '+f2(rr)+' USD nếu chạm SL · rủi ro '+f2(rk.rr)+'% vốn: '+(lot>=.01?lot.toFixed(2).replace('.',',')+' lot':'không đủ cho 0,01 lot'),x0+4,ysl+(len?14:-5),P.mute)}
   g={nut:[['a',x0,ya],['sl',x1,ysl],['tp',x1,ytp]],trong:(x,yy)=>x>=x0-3&&x<=x1+3&&yy>=Math.min(ysl,ytp)-3&&yy<=Math.max(ysl,ytp)+3}}
  else if(h.k==='mt'){X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.stroke();const gc=Math.atan2(yb-ya,xb-xa),L=12;X.fillStyle=col;X.beginPath();X.moveTo(xb,yb);X.lineTo(xb-L*Math.cos(gc-.42),yb-L*Math.sin(gc-.42));X.lineTo(xb-L*Math.cos(gc+.42),yb-L*Math.sin(gc+.42));X.closePath();X.fill();
   g={nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>doan(xa,ya,xb,yb,x,yy)<=6}}
  else if(h.k==='tia'){const dx=xb-xa,dy=yb-ya,he=dx||dy?(pw+ph)*3/Math.hypot(dx,dy):0,xe=xa+dx*he,ye=ya+dy*he;X.beginPath();X.moveTo(xa,ya);X.lineTo(xe,ye);X.stroke();g={nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>doan(xa,ya,xe,ye,x,yy)<=6}}
  else if(h.k==='doc'){const Xv=Math.round(xa)+.5;X.beginPath();X.moveTo(Xv,0);X.lineTo(Xv,ph);X.stroke();chu(vn(h.a.t),Xv+5,ph-8,col);g={nut:[],trong:x=>Math.abs(x-Xv)<=5}}
  else if(h.k==='kenh'){const yd=y(h.a.p+h.d),ye=y(h.b.p+h.d);if(yd==null||ye==null)continue;X.globalAlpha=.08;X.fillStyle=col;X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.lineTo(xb,ye);X.lineTo(xa,yd);X.closePath();X.fill();X.globalAlpha=1;
   X.beginPath();X.moveTo(xa,ya);X.lineTo(xb,yb);X.moveTo(xa,yd);X.lineTo(xb,ye);X.stroke();X.setLineDash([4,4]);X.lineWidth=1;X.beginPath();X.moveTo(xa,(ya+yd)/2);X.lineTo(xb,(yb+ye)/2);X.stroke();X.setLineDash([]);
   g={nut:[['a',xa,ya],['b',xb,yb],['d',(xa+xb)/2,(yd+ye)/2]],trong:(x,yy)=>doan(xa,ya,xb,yb,x,yy)<=6||doan(xa,yd,xb,ye,x,yy)<=6}}
  else if(h.k==='elip'){const cx=(xa+xb)/2,cy=(ya+yb)/2,rx=Math.abs(xb-xa)/2||1,ry=Math.abs(yb-ya)/2||1;X.beginPath();X.ellipse(cx,cy,rx,ry,0,0,7);X.globalAlpha=.08;X.fillStyle=col;X.fill();X.globalAlpha=1;X.stroke();
   g={nut:[['a',xa,ya],['b',xb,yb]],trong:(x,yy)=>((x-cx)/(rx+4))**2+((yy-cy)/(ry+4))**2<=1}}
  else if(h.k==='but'){const ps=(h.pts||[]).map(q=>[vx(q.t),y(q.p)]).filter(q=>q[0]!=null&&q[1]!=null);if(ps.length<2)continue;X.lineJoin='round';X.lineCap='round';X.beginPath();ps.forEach((q,i)=>i?X.lineTo(q[0],q[1]):X.moveTo(q[0],q[1]));X.stroke();
   if(sel){X.setLineDash([3,3]);X.lineWidth=1;const xs=ps.map(q=>q[0]),ys=ps.map(q=>q[1]);X.strokeRect(Math.min(...xs)-4,Math.min(...ys)-4,Math.max(...xs)-Math.min(...xs)+8,Math.max(...ys)-Math.min(...ys)+8);X.setLineDash([])}
   g={nut:[],trong:(x,yy)=>ps.some((q,i)=>i&&doan(ps[i-1][0],ps[i-1][1],q[0],q[1],x,yy)<=6)}}
  else if(h.k==='chu'){const w=chu(h.chu,xa+7,ya+4,h.mau||P.fg);X.fillStyle=col;X.beginPath();X.arc(xa,ya,3,0,7);X.fill();if(sel){X.strokeStyle=col;X.lineWidth=1;X.strokeRect(xa+3.5,ya-8.5,w+8,16)}g={nut:[],trong:(x,yy)=>x>=xa-6&&x<=xa+w+12&&yy>=ya-10&&yy<=ya+8}}
  if(!g)continue;if(sel)for(const[,x,yy]of g.nut)cham(x,yy,col);VE.hit.push({id:h.id,...g})}}
function veTrung(x,yy){const ds=[...VE.hit].reverse(),c=ds.find(g=>g.id===VE.chon);for(const g of(c?[c]:[]))for(const[k,nx,ny]of g.nut)if(Math.hypot(x-nx,yy-ny)<=8)return{id:g.id,nut:k};for(const g of ds)if(g.trong(x,yy))return{id:g.id,nut:null};return null}
if(LW){VTB.setAttribute('data-thu','');$('.stage').appendChild(VTB);$('.stage').appendChild(VGOI);veDoc();veTb();
 const vePt=e=>{const r=LWE.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}},moiId=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,5),xong=id=>{const h=VE.ds.find(x=>x.id===id);if(h&&VE.mau)h.mau=VE.mau;VE.tam=VE.keo=null;VE.chon=id;veLuu();veCong('tro')};
 // đang cầm một công cụ: lớp phủ nhận chuột, biểu đồ đứng yên
 LWO.addEventListener('pointerdown',e=>{if(VE.cong==='tro'||!D)return;e.preventDefault();const m=vePt(e),q=veToa(m.x,m.y);if(!q)return;const c=VE.cong,id=moiId();
  if(c==='ngang'||c==='doc'){VE.ds.push({id,k:c,a:q});xong(id);return}
  if(c==='chu'){const o=document.createElement('input');o.className='venhap';o.maxLength=80;o.placeholder='Ghi chú, Enter để lưu';o.style.left=Math.min(m.x,LWE.clientWidth-230)+'px';o.style.top=(m.y-14)+'px';$('.stage').appendChild(o);setTimeout(()=>o.focus(),0);
   let da=0;const dong=luu=>{if(da)return;da=1;const v=o.value.trim();o.remove();if(luu&&v){VE.ds.push({id,k:c,a:q,chu:v});xong(id)}else veCong('tro')};o.addEventListener('keydown',ev=>{ev.stopPropagation();if(ev.key==='Enter')dong(1);else if(ev.key==='Escape')dong(0)});o.addEventListener('blur',()=>dong(1));return}
  if(c==='do'){VE.do={a:q,b:q};VE.keo={moi:'do',m}}else{VE.tam=c==='vt'?{id,k:c,a:q,b:{...q},sl:q.p,tp:q.p}:c==='but'?{id,k:c,a:q,pts:[q]}:c==='kenh'?{id,k:c,a:q,b:{...q},d:0}:{id,k:c,a:q,b:{...q}};VE.keo={moi:1,m}}
  try{LWO.setPointerCapture(e.pointerId)}catch(_){}lwPhu()});
 LWO.addEventListener('pointermove',e=>{if(!VE.keo||!VE.keo.moi)return;const m=vePt(e),q=veToa(m.x,m.y);if(!q)return;if(VE.keo.moi==='do')VE.do.b=q;else{const h=VE.tam;if(h.k==='but'){const l=VE.keo.l||VE.keo.m;if(Math.hypot(m.x-l.x,m.y-l.y)>=3){h.pts.push(q);VE.keo.l=m}}else{h.b=q;if(h.k==='vt'){h.sl=q.p;h.tp=h.a.p+(h.a.p-q.p)*2;h.b={t:q.t,p:h.a.p}}else if(h.k==='kenh')h.d=LW.nen.coordinateToPrice(44)-LW.nen.coordinateToPrice(0)}}lwPhu()});
 LWO.addEventListener('pointerup',e=>{if(!VE.keo||!VE.keo.moi)return;const m=vePt(e),xa=Math.hypot(m.x-VE.keo.m.x,m.y-VE.keo.m.y)>6;
  if(VE.keo.moi==='do'){VE.keo=null;if(!xa)VE.do=null;veCong('tro');return}const h=VE.tam;if(xa&&h&&!(h.k==='vt'&&h.sl===h.a.p)){VE.ds.push(h);xong(h.id)}else{VE.tam=VE.keo=null;lwPhu()}});
 // đang ở chế độ chọn: bấm trúng hình thì chọn và kéo hình đó, biểu đồ không trượt theo
 let chan=0;LWE.addEventListener('pointerdown',e=>{chan=0;if(VE.cong!=='tro'||!D)return;if(VE.do){VE.do=null;lwPhu()}if(VE.an)return;const m=vePt(e),h=veTrung(m.x,m.y);
  if(!h){if(VE.chon){VE.chon=null;veTb();lwPhu()}return}chan=1;e.stopPropagation();VE.chon=h.id;VE.keo={id:h.id,nut:h.nut,q0:veToa(m.x,m.y),goc:JSON.parse(JSON.stringify(VE.ds.find(x=>x.id===h.id)))};veTb();lwPhu()},true);
 for(const ev of['mousedown','touchstart'])LWE.addEventListener(ev,e=>{if(chan)e.stopPropagation()},true);
 addEventListener('pointermove',e=>{const k=VE.keo;if(!k||k.moi||!k.q0)return;const m=vePt(e),q=veToa(m.x,m.y),h=VE.ds.find(x=>x.id===k.id);if(!q||!h)return;const dp=q.p-k.q0.p,dT=q.t-k.q0.t,g=k.goc,di=(pt)=>({t:pt.t+dT,p:pt.p+dp});
  if(k.nut==='sl')h.sl=g.sl+dp;else if(k.nut==='tp')h.tp=g.tp+dp;else if(k.nut==='d')h.d=g.d+dp;else if(k.nut==='b')h.b=di(g.b);else if(k.nut==='a'&&h.k!=='vt')h.a=di(g.a);
  else{h.a=di(g.a);if(g.b)h.b=h.k==='vt'?{t:g.b.t+dT,p:g.a.p+dp}:di(g.b);if(h.k==='vt'&&k.nut!=='a'){h.sl=g.sl+dp;h.tp=g.tp+dp}if(g.pts)h.pts=g.pts.map(di)}lwPhu()});
 addEventListener('pointerup',()=>{if(VE.keo&&!VE.keo.moi){VE.keo=null;veLuu()}chan=0});
 addEventListener('keydown',e=>{if(/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||''))return;if((e.ctrlKey||e.metaKey)&&(e.key==='z'||e.key==='Z')){e.preventDefault();veHoan()}else if((e.key==='Delete'||e.key==='Backspace')&&VE.chon){e.preventDefault();veXoa()}else if(e.key==='Escape'&&(VE.cong!=='tro'||VE.do||VE.chon)){VE.do=null;VE.chon=null;veCong('tro')}})}
// --- tài khoản MT5: chỉ đọc, chỉ tài khoản demo. Thẻ bên phải và các đường trên biểu đồ chỉ nói về mã đang xem.
let TK=null,tkH='';const tkMa=()=>ma||((((typeof MA!=='undefined'&&MA.selectedOptions)||[])[0]||{}).textContent||'').split(' · ')[0]||'XAUUSDp',tkLenh=()=>TK&&TK.san_sang?TK.lenh.filter(x=>x.ma===tkMa()):[];
function tkVe(){const el=$('#tk');if(!el)return;let h='<h3>Tài khoản MT5'+(TK&&TK.san_sang?' <span class="hl ok">'+esc(TK.loai)+'</span>':'')+'</h3>';
 if(!TK)h+='<p class="why">Đang đọc tài khoản…</p>';
 else if(!TK.san_sang)h+=`<p class="why">Chưa đọc được tài khoản: ${esc(TK.ly_do||'chưa rõ lý do')}. Trang chỉ đọc tài khoản demo đang mở trong MT5.</p>`;
 else{const sym=tkMa(),tien=v=>`<span class="${v>0?'gain':v<0?'loss':''}">${(v>0?'+':v<0?'−':'')+f2(Math.abs(v))} ${esc(TK.tien)}</span>`,mo=TK.lenh.filter(x=>x.ma===sym),cho=(TK.cho||[]).filter(x=>x.ma===sym),dong=(TK.da_dong||[]).filter(x=>x.ma===sym).slice(0,5),khac=TK.lenh.length-mo.length;
  h+=kv('Tài khoản',esc(TK.so)+' · '+esc(TK.may_chu))+kv('Số dư',f2(TK.so_du)+' '+esc(TK.tien))+kv('Vốn hiện có',f2(TK.von)+' '+esc(TK.tien))+kv('Lãi lỗ đang treo',tien(TK.treo))+kv('Ký quỹ còn trống',f2(TK.ky_quy_con)+' '+esc(TK.tien));
  h+=`<h3>Lệnh đang mở trên ${esc(sym)}</h3>`+(mo.length?mo.map(l=>`<div class="tkl"><span class="dir ${l.huong==='MUA'?'up':'dn'}">${l.huong==='MUA'?'▲ MUA':'▼ BÁN'}</span><b>${f2(l.lot)} lot · ${fp(l.vao)}</b>${tien(l.lai)}<small>SL ${l.sl!=null?fp(l.sl):'chưa đặt'} · TP ${l.tp!=null?fp(l.tp):'chưa đặt'}${l.nguon?' · '+esc(l.nguon):''}</small></div>`).join(''):'<p class="why">Không có lệnh nào đang mở trên mã này.</p>')
   +(khac>0?`<p class="why">Còn ${khac} lệnh đang mở ở mã khác.</p>`:'');
  if(cho.length)h+='<h3>Lệnh chờ</h3>'+cho.map(c=>`<div class="tkl"><span class="dir">${esc(c.loai)}</span><b>${f2(c.lot)} lot · ${fp(c.gia)}</b><small>SL ${c.sl!=null?fp(c.sl):'chưa đặt'} · TP ${c.tp!=null?fp(c.tp):'chưa đặt'}</small></div>`).join('');
  if(dong.length)h+=`<h3>Đã đóng gần đây trên ${esc(sym)}</h3>`+dong.map(x=>`<div class="tkl"><span class="dir ${x.huong==='MUA'?'up':'dn'}">${x.huong==='MUA'?'▲ MUA':'▼ BÁN'}</span><b>${f2(x.lot)} lot · ${fp(x.gia)}</b>${tien(x.lai)}<small>${vn(Date.parse(x.luc)/1000)}${x.nguon?' · '+esc(x.nguon):''}</small></div>`).join('');
  h+='<p class="why" style="margin-top:10px">Chỉ đọc tài khoản demo; không đặt, sửa hay đóng lệnh. <a href="/tai-khoan">Báo cáo đầy đủ</a> · <a href="/cac-tai-khoan">Mọi tài khoản đã nối</a></p>'}
 if(h!==tkH){tkH=h;el.innerHTML=h}tktVe()}
// dải tài khoản cố định: vốn, lãi treo, ký quỹ trống, tổng rủi ro nếu mọi lệnh mở cùng chạm dừng lỗ, các lệnh mở, phiên và tin USD kế tiếp
let tktH='',TTOI=null;const PHIEN=[['Á',0,9],['Âu',7,16],['Mỹ',12,21]];
async function ttTai(){try{TTOI=await (await fetch('/api/tin-toi',{cache:'no-store'})).json()}catch(e){}tktVe()}ttTai();setInterval(ttTai,120000);
function tktVe(){const el=$('#tkt');if(!el)return;let h='';
 if(!TK)h='<p class="why">Đang đọc tài khoản…</p>';
 else if(!TK.san_sang)h=`<p class="why">Chưa đọc được tài khoản: ${esc(TK.ly_do||'chưa rõ lý do')}.</p>`;
 else{const t=v=>(v>0?'+':v<0?'−':'')+f2(Math.abs(v)),R=TK.rui_ro||{},pct=R.pct==null?null:+R.pct,muc=pct==null?'':pct<2?'':pct<5?' vua':' cao';
  h=`<div class="th"><b>Tài khoản ${esc(TK.so||'')}</b><span class="hl ok">${esc(TK.loai||'')}</span></div>`
   +`<div class="tg"><div><small>Vốn hiện có</small><b>${f2(TK.von)}</b></div><div><small>Lãi lỗ treo</small><b class="${TK.treo>0?'gain':TK.treo<0?'loss':''}">${t(TK.treo)}</b></div><div><small>Ký quỹ trống</small><b>${f2(TK.ky_quy_con)}</b></div></div>`;
  if(TK.lenh.length)h+=`<div class="rrb${muc}" title="Tổng số tiền mất nếu mọi lệnh đang mở cùng chạm dừng lỗ, so với vốn hiện có"><span>Đang chịu rủi ro: <b>${f2(R.tong||0)} ${esc(TK.tien)}${pct!=null?' = '+String(pct.toFixed(1)).replace('.',',')+'% vốn':''}</b></span>`
   +`<div class="tr"><i style="width:${Math.min(100,Math.max(2,pct||0))}%"></i></div>`+(R.khong_sl?`<span class="loss">${R.khong_sl} lệnh không có dừng lỗ: rủi ro không giới hạn.</span>`:'')+(R.khong_tinh?`<span>${R.khong_tinh} lệnh chưa tính được rủi ro.</span>`:'')+'</div>'
   +TK.lenh.slice(0,3).map(l=>`<div class="ln"><span class="dir ${l.huong==='MUA'?'up':'dn'}">${l.huong==='MUA'?'▲':'▼'}</span>${esc(String(l.ma).replace(/p$/,''))} ${f2(l.lot)} lot · ${fp(l.vao)}<em class="${l.lai>0?'gain':l.lai<0?'loss':''}">${t(l.lai)}</em></div>`).join('')
   +(TK.lenh.length>3?`<div class="ln">và ${TK.lenh.length-3} lệnh khác</div>`:'');
  else h+='<div class="ln">Không có lệnh nào đang mở.</div>'}
 const now=new Date(),g=now.getUTCHours()+now.getUTCMinutes()/60,mo=PHIEN.filter(([,a,b])=>g>=a&&g<b).map(x=>x[0]);
 const ke=PHIEN.map(([n,a])=>[n,(a-g+24)%24]).filter(([n])=>!mo.includes(n)).sort((a,b)=>a[1]-b[1])[0];
 const t0=TTOI&&TTOI.ds&&TTOI.ds[0],tin=t0?t0.luc:(D&&D.luat&&D.luat.tin&&(D.luat.tin.sap_toi||[])[0]),phut=tin?Math.round((Date.parse(tin)-Date.now())/60000):null;
 h+=`<div class="ph"><span>Phiên: <b>${mo.length?mo.join(', '):'nghỉ'}</b>${ke?' · '+ke[0]+' mở sau '+(ke[1]>=1?Math.floor(ke[1])+' giờ ':'')+Math.round(ke[1]%1*60)+' phút':''}</span>`
  +(phut!=null&&phut>=0?`<span title="Số đo trên các lần ra tin 2015–2026 (cong-cu/phan_ung_tin.py): giá thường chạy bao xa sau tin. Chiều giá sau tin không đoán được: mọi quy tắc thử đều quanh 50%.">Tin USD mạnh: <b>${t0?esc(t0.ten)+' · ':''}${phut<60?phut+' phút nữa':Math.floor(phut/60)+' giờ '+(phut%60)+' phút nữa'}</b>`
   +(t0&&t0.d15_tv!=null?` · 15 phút sau tin thường chạy ~${String(t0.d15_tv).replace('.',',')} giá, 10% số lần trên ${String(t0.d15_p90).replace('.',',')} giá; chiều không đoán được`:'')+'</span>':'')+(D&&D.luat&&D.luat.tin&&D.luat.tin.dang_ne?'<span class="loss">Đang trong giờ né tin</span>':'')+'</div>';
 if(h!==tktH){tktH=h;el.innerHTML=h}}
// thẻ chuyển của cột phải: nhớ thẻ đang chọn
let CTAB='cb';try{CTAB=localStorage.getItem('so-ctab')||'cb'}catch(e){}
function ctabDat(t){CTAB=t;const c=$('.col');if(c)c.dataset.tab=t;document.querySelectorAll('.ctab button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.t===t)));
 try{localStorage.setItem('so-ctab',t)}catch(e){}if(t==='cb'){try{fresh.clear();cbMoi()}catch(e){}}}       // lúc nạp trang 'fresh' chưa được khai báo: bỏ qua
document.querySelectorAll('.ctab button').forEach(b=>b.addEventListener('click',()=>ctabDat(b.dataset.t)));ctabDat(CTAB);setInterval(tktVe,30000);
async function tkTai(){try{const r=await fetch('/api/tai-khoan',{cache:'no-store'});TK=await r.json()}catch(e){TK={san_sang:false,ly_do:e.message}}tkVe();if(LW)lwPhu()}
// --- nhật ký điểm vào: mỗi điểm vào còn hiệu lực được máy chủ ghi lại lúc nó xuất hiện rồi theo dõi kết quả; bấm một dòng để xem lại trên biểu đồ
let NK=null,nkH='';const NKT={cho_khop:['Chờ khớp','song'],dang_mo:['Đang mở','song'],thang:['Thắng','ok'],thua:['Thua','xau'],het_gio:['Hết giờ',''],khong_khop:['Không khớp',''],huy:['Hủy trước khi khớp',''],thay:['Tín hiệu mới thay','']},nkR=v=>(v>0?'+':v<0?'−':'')+f2(Math.abs(v))+'R';
function lwToi(t){if(!LW||!D)return;const cs=D.candles;let a=0,b=cs.length-1;while(a<b){const m=(a+b+1)>>1;if(cs[m][0]<=t)a=m;else b=m-1}LW.cho={from:a-90,to:a+70};LW.chart.timeScale().setVisibleLogicalRange(LW.cho)}
function nkVe(){const el=$('#nk');if(!el)return;let h='<h3>Nhật ký điểm vào</h3>';
 if(!NK)h+='<p class="why">Đang đọc nhật ký…</p>';
 else if(!NK.bat)h+='<p class="why">Nhật ký đang tắt trong cấu hình (mục nhat_ky.bat).</p>';
 else{const sym=tkMa(),ds=(NK.ds||[]).filter(x=>x.sym===sym),tom=(NK.tom||[]).filter(t=>t.sym===sym),khac=(NK.ds||[]).filter(x=>x.sym!==sym&&(x.tt==='cho_khop'||x.tt==='dang_mo')).length;
  if(tom.length)h+=tom.map(t=>`<div class="kv"><span>${esc(t.ten)}</span><b>${t.thang} thắng · ${t.thua} thua${t.khac?' · '+t.khac+' không tính':''} · <span class="${t.tong_r>0?'gain':t.tong_r<0?'loss':''}">${nkR(t.tong_r)}</span>${t.song?' · '+t.song+' còn sống':''}</b></div>`).join('');
  h+=ds.length?ds.slice(0,6).map(x=>{const[tt,lop]=NKT[x.tt]||[x.tt,''],mua=x.huong==='MUA';return `<button type="button" class="nkd${plan&&plan.ma==='nk:'+x.id?' sel':''}" data-id="${x.id}" title="Bấm để xem lại điểm vào này trên biểu đồ"><i class="${lop}"></i><b>${mua?'▲ MUA':'▼ BÁN'} ${fp(x.vao)}</b><em class="${lop==='ok'?'gain':lop==='xau'?'loss':''}">${tt}${x.r!=null?' '+nkR(x.r):''}</em><small>${vn(Date.parse(x.luc)/1000)} · ${esc(x.ten)} · SL ${fp(x.sl)} · TP ${fp(x.tp[x.tp.length-1])}${x.cham_tp1&&x.tt!=='thang'?' · đã chạm TP1':''}</small></button>`}).join('')
   :`<p class="why">Chưa có điểm vào nào được ghi trên ${esc(sym)}.</p>`;
  if(khac)h+=`<p class="why">Còn ${khac} điểm vào đang sống ở mã khác.</p>`;
  h+='<p class="why" style="margin-top:10px">Chấm xanh nhấp nháy là điểm vào còn sống. <a href="/nhat-ky">Xem toàn bộ nhật ký</a></p>';
  for(const e of NK.loi||[])h+=`<p class="stale">${esc(e)}</p>`}
 if(h===nkH)return;nkH=h;el.innerHTML=h;
 el.querySelectorAll('.nkd').forEach(b=>b.addEventListener('click',()=>{const x=(NK.ds||[]).find(r=>r.id===+b.dataset.id);if(x)nkChon(x)}))}
function nkChon(x,giu){const k='nk:'+x.id;
   if(plan&&plan.ma===k&&!giu){plan=null;planTat=1}else{const t=Date.parse(x.luc)/1000;plan={ma:k,nk:x,ten:x.ten+' · ghi lúc '+vn(t),huong:x.huong,vao:x.vao,sl:x.sl,tp:x.tp,rr:x.rr,rui_ro_gia:Math.abs(x.vao-x.sl),ly_do:x.ly_do,hieu_luc:x.tt==='cho_khop'||x.tt==='dang_mo'?true:false,vi_sao_het:['Đây là điểm vào đã ghi trong nhật ký; kết quả: '+(NKT[x.tt]||[x.tt])[0]+'.']};planTat=0;lwToi(t)}
   nkH='';nkVe();draw();dvVe();if(hep()&&!fsOn())CP.scrollIntoView({behavior:'smooth',block:'start'})}
let nkMo=+(new URLSearchParams(location.search).get('nk')||0);
async function nkTai(){try{const r=await fetch('/api/nhat-ky',{cache:'no-store'});NK=await r.json()}catch(e){NK={bat:true,ds:[],tom:[],loi:[e.message]}}nkVe();if(nkMo&&D&&NK.ds){const x=NK.ds.find(r=>r.id===nkMo);nkMo=0;const co=!!(x&&x.sym===tkMa());if(co)nkChon(x,1);if(ANH)anhXong(co,co?Date.parse(x.luc)/1000:0)}}
function anhXong(co,t){setTimeout(()=>{draw();requestAnimationFrame(()=>{if(co&&LW)lwToi(t);draw();setTimeout(()=>requestAnimationFrame(()=>{document.documentElement.dataset.anh=co?'san':'khong-thay'}),300)})},700)}
// --- cảnh báo
const CB=$('#cb'),TS=document.createElement('div');TS.className='toasts';document.body.appendChild(TS);let seen=null,snd=0,fresh=new Set(),cbLoc='';try{snd=+localStorage.getItem('so-snd')||0;cbLoc=localStorage.getItem('so-cbloc')||''}catch(e){}
const CBL={bot:'BOT',ba_khung:'3 KHUNG',dinh_day:'ĐỈNH/ĐÁY'},cbNhom=a=>{const k=String(a.khoa||'').split('|')[0];return CBL[k]?k:'pp'},MIEN=/\s*Đây là tín hiệu của luật[^.]*\./g;
function cbMoi(){const b=$('#cb-moi');if(!b)return;const n=fresh.size;b.hidden=!n||CTAB==='cb';b.textContent=n}
function beep(){try{const a=new(window.AudioContext||window.webkitAudioContext)(),o=a.createOscillator(),g=a.createGain();o.frequency.value=880;g.gain.value=.08;o.connect(g);g.connect(a.destination);o.start();o.stop(a.currentTime+.2)}catch(e){}}
function toast(a){const d=document.createElement('div');d.className='toast';d.innerHTML='<b>'+esc(a.tieu_de)+'</b>'+esc(a.noi_dung);d.addEventListener('click',()=>d.remove());TS.appendChild(d);setTimeout(()=>d.remove(),20000)}
async function cb(){let j;try{const r=await fetch('/api/canh-bao',{cache:'no-store'});if(!r.ok)throw 0;j=await r.json()}catch(e){return}
 const ds=j.ds||[];if(seen!==null)for(const a of ds.filter(a=>a.id>seen).reverse()){fresh.add(a.id);toast(a);if(snd)beep();
  if(window.Notification&&Notification.permission==='granted')try{new Notification(a.tieu_de,{body:a.noi_dung,tag:'so-'+a.id})}catch(e){}}
 seen=ds.length?Math.max(...ds.map(a=>a.id)):(seen||0);const perm=window.Notification?Notification.permission:'none';
 const kh=D&&D.khac_vang;let h='<h3>Cảnh báo</h3>';if(kh)h+='<p class="why">Cảnh báo theo luật trong sổ của bạn chỉ có cho vàng.</p>';else if(j.ly_do)h+=`<p class="why">${esc(j.ly_do)}</p>`;
 if(!kh&&ds.length){const co=[...new Set(ds.map(cbNhom))];
  if(co.length>1)h+='<div class="cbl" role="group" aria-label="Lọc cảnh báo">'+[['','Tất cả'],...co.map(k=>[k,CBL[k]||'Phương pháp'])].map(([k,t])=>`<button type="button" data-k="${k}" aria-pressed="${cbLoc===k}">${esc(t)}</button>`).join('')+'</div>';
  const gop=[];for(const a of ds.filter(a=>!cbLoc||cbNhom(a)===cbLoc)){const nd=String(a.noi_dung||'').replace(MIEN,'').trim(),cu=gop[gop.length-1];
   if(cu&&cu.tieu_de===a.tieu_de&&cu.nd===nd){cu.n++;cu.moi=cu.moi||fresh.has(a.id)}else gop.push({...a,nd,n:1,moi:fresh.has(a.id)})}
  h+=gop.slice(0,8).map(a=>{const nh=cbNhom(a),ban=/BÁN/.test(a.tieu_de),mua=/MUA/.test(a.tieu_de),khung=(a.tieu_de.match(/M\d+|H\d+/)||[''])[0];
   return `<details class="al2${a.moi?' new':''}"><summary><span class="tag">${CBL[nh]||'PP'}</span>${ban||mua?`<span class="dir ${mua?'up':'dn'}">${mua?'▲ MUA':'▼ BÁN'}</span>`:''}${khung?'<b>'+khung+'</b>':''}<span class="nd">${esc(a.nd||a.tieu_de)}</span>${a.n>1?'<em>×'+a.n+'</em>':''}<time>${vn(Date.parse(a.luc)/1000)}</time></summary><p><b>${esc(a.tieu_de)}.</b> ${esc(a.nd)}</p></details>`}).join('')
   +(gop.length?'':'<p class="why">Không có cảnh báo nào của nhóm này.</p>')
   +'<p class="why" style="margin-top:6px">Đây là tín hiệu của luật, không phải lệnh; chưa luật nào được chứng minh có lãi.</p>'}
 else if(!kh)h+='<p class="why">Chưa có cảnh báo nào.</p>';
 h+='<details class="plct" style="margin-top:8px"><summary>Trang báo khi nào</summary><p class="why">Khi một phương pháp đang bật có điểm vào còn hiệu lực, trang báo bằng thông báo nổi và nhắc lại mỗi 5 phút chừng nào điểm vào còn sống. Chưa mô hình nào trong dữ liệu đạt tỷ lệ thắng 90%, nên trang không lọc theo ngưỡng đó; mỗi lần báo đều ghi tỷ lệ có lãi đã đo. Khi nút Kỷ luật ở thanh phương pháp đang bật, trang chỉ báo điểm vào có số đo giữ được ở cả hai nửa dữ liệu.</p></details>';
 h+=`<div class="chips" style="margin-top:10px"><button type="button" class="chip" id="cbn" aria-pressed="${perm==='granted'}"><i></i>Thông báo trên máy</button><button type="button" class="chip" id="cbs" aria-pressed="${!!snd}"><i></i>Âm thanh</button></div>`;
 CB.innerHTML=h;cbMoi();
 CB.querySelectorAll('.cbl button').forEach(b=>b.addEventListener('click',()=>{cbLoc=b.dataset.k;try{localStorage.setItem('so-cbloc',cbLoc)}catch(e){}cb()}));
 $('#cbn').addEventListener('click',async()=>{if(!window.Notification){alert('Trình duyệt này không hỗ trợ thông báo.');return}if(Notification.permission==='denied'){alert('Bạn đã chặn thông báo cho trang này; hãy mở lại trong cài đặt của trình duyệt.');return}await Notification.requestPermission();cb()});
 $('#cbs').addEventListener('click',()=>{snd=snd?0:1;try{localStorage.setItem('so-snd',snd)}catch(e){}if(snd)beep();cb()})}
// --- hỏi AI
const A=$('#ai'),HD=a=>a==='MUA'?'MUA':a==='BAN'?'BÁN':'ĐỨNG NGOÀI';
function kq(r){if(!r)return'';let h=`<p class="why">Lượt hỏi lúc ${vn(Date.parse(r.luc)/1000)} · giá ${f2(r.bid)}</p>`;
 if(r.loai!=='signal'||!r.tin_hieu)return h+`<p class="stale">AI không trả tín hiệu (${esc(r.loai)}${r.loi?': '+esc(r.loi):''}).</p>`;
 const t=r.tin_hieu,k=r.kiem_tra||{};AIR=r;h+=`<p class="verdict">${HD(t.hanh_dong)}${t.hanh_dong!=='DUNG_NGOAI'?' · '+esc(t.kieu_vao):''}</p>`;
 if(t.hanh_dong!=='DUNG_NGOAI')h+=kv('Giá vào',f2(t.gia_vao))+kv('SL',f2(t.sl))+kv('TP1 / TP2 / TP3',f2(t.tp1)+' / '+f2(t.tp2)+' / '+f2(t.tp3))+kv('Hiệu lực',(t.hieu_luc_phut||0)+' phút');
 h+=kv('Độ tin cậy AI tự chấm',(t.do_tin_cay??'—')+'/100')+kv('Kiểm tra của bộ luật',k.trang_thai==='hop_le'?'hợp lệ':k.trang_thai==='dung_ngoai'?'đứng ngoài':'KHÔNG hợp lệ')+kv('Chi phí lượt này',r.chi_phi_usd!=null?f2(r.chi_phi_usd)+' USD':'—');
 if(t.hanh_dong!=='DUNG_NGOAI'&&t.sl!=null)h+='<button type="button" class="ghost nho" id="ai-ve" style="margin:8px 0 2px">Vẽ phương án của AI lên biểu đồ</button>';
 if(k.ly_do&&k.ly_do.length)h+=`<p class="stale">Bộ kiểm tra loại vì: ${esc(k.ly_do.join(', '))}</p>`;
 return h+`<p class="why"><b>Lý do AI nêu:</b> ${esc(t.ly_do)}</p>`+(t.dieu_kien_huy?`<p class="why"><b>Hủy khi:</b> ${esc(t.dieu_kien_huy)}</p>`:'')}
async function ai(last){let st;try{st=await(await fetch('/api/ai',{cache:'no-store'})).json()}catch(e){A.innerHTML='<h3>AI phân tích điểm vào</h3><p class="stale">Không tải được trạng thái.</p>';return}
 let h='<h3>AI phân tích điểm vào</h3><p class="why">Gửi nến M5 đến H1 cùng các vùng giá cho Claude theo đúng lời nhắc v3 của bạn, rồi kiểm tra câu trả lời bằng bộ luật của bạn.</p>'
  +kv('Hôm nay',st.hom_nay+'/'+st.moi_ngay+' lượt')+kv('Đã dùng',f2(st.da_tieu_usd)+' / '+f2(st.ngan_sach_usd)+' USD')
  +`<button class="go" id="ask" type="button" ${st.chan.length?'disabled':''}>Hỏi AI một lượt (khoảng ${f2(st.uoc_tinh_usd)} USD)</button>`;
 for(const c of st.chan)h+=`<p class="why">• ${esc(c)}</p>`;h+=kq(last||st.gan_day[0]);
 h+='<p class="why">Theo sổ chạy bóng của bạn, AI gọi lệnh thắng 41% số lệnh và âm 4,82R khi phát lại 19 ngày. Đây là ý kiến của một mô hình, không phải lời khuyên đầu tư. Trang này không đặt lệnh.</p>';
 A.innerHTML=h;const av=$('#ai-ve');if(av)av.addEventListener('click',()=>{const r=AIR;if(!r||!r.tin_hieu)return;const t=r.tin_hieu,k=r.kiem_tra||{},vao=t.gia_vao!=null?t.gia_vao:r.bid,rui=Math.abs(vao-t.sl),
   tp=[t.tp1,t.tp2,t.tp3].filter(v=>v!=null),con=k.trang_thai==='hop_le'&&(Date.now()-Date.parse(r.luc))/60000<=(t.hieu_luc_phut||0);
  plan={ma:'ai',ten:'AI',huong:t.hanh_dong,vao,sl:t.sl,tp,rr:tp.map(v=>rui?Math.abs(v-vao)/rui:null),rui_ro_gia:rui,vung:null,hieu_luc:con};view.off=0;draw();$('#cp').scrollIntoView({behavior:'smooth',block:'nearest'})});
 const b=$('#ask');if(b)b.addEventListener('click',async()=>{if(!confirm('Hỏi AI một lượt sẽ tốn khoảng '+f2(st.uoc_tinh_usd)+' USD tiền API của bạn. Tiếp tục?'))return;
  b.disabled=true;b.textContent='Đang hỏi AI, chờ tối đa 90 giây…';try{const r=await fetch('/api/ai',{method:'POST',headers:{'X-So-Cong-Khai':'1'}});if(!r.ok)throw new Error(await r.text());
   const j=await r.json();if(!j.ok){await ai();alert(j.chan.join('\n'));return}await ai(j.ket_qua)}catch(e){await ai();alert('Không hỏi được AI: '+e.message)}})}
// --- phân tích điểm vào, SL, TP theo các luật của chủ dự án
const PTB=$('#pt'),CP=$('#cp'),hep=()=>matchMedia('(max-width:980px)').matches;
PTB.addEventListener('click',async e=>{const b=e.target.closest('.dlb');if(!b)return;b.disabled=true;b.textContent='Đang đo lại…';try{await fetch('/api/do-lai',{method:'POST',headers:{'X-So-Cong-Khai':'1'}})}catch(_){}let n=0;const cho=async()=>{await dlTai();if(DL&&DL.dang&&n++<40)setTimeout(cho,5000)};setTimeout(cho,3000)});   // nút "Đo lại ngay" (kiểm trên giá mới)
const hocMoc=k=>{const r=(HOC&&HOC.luat&&HOC.luat[k])||{};return{tu:r.tu||HOC.tu,cat:r.cat||HOC.cat,den:r.den||HOC.den}};
function hocHtml(p){const k=p.ma.split(':')[0],kh=PTR&&PTR.khac_vang,dau='<div class="kc"><b>'+(kh?'Đo trên dữ liệu của chính mã này':'Dữ liệu nhiều năm')+'</b>';
 if(!HOC)return dau+'<p class="why">'+(kh?'Đang chạy lại phương pháp trên nến 5 phút của mã này từ đầu năm; lần đầu mỗi ngày mất khoảng 10 giây…':'Đang chạy lại luật trên dữ liệu nhiều năm; lần đầu mỗi ngày mất khoảng một phút…')+'</p></div>';
 if(!HOC.san_sang)return dau+`<p class="stale">Không tính được: ${esc((HOC.loi||[]).join('; ')||'chưa rõ lý do')}</p></div>`;
 const r=HOC.luat[k];if(!r)return dau+'<p class="stale">Không chạy lại được luật này trên dữ liệu nhiều năm.</p></div>';
 const bc=(PTR&&PTR.boi_canh)||{},pc=v=>v.toFixed(1).replace('.',',')+'%',sg=v=>(v>0?'+':v<0?'−':'')+f2(Math.abs(v)),mau=v=>v>0?'gain':'loss',ng=s=>new Date(s).toLocaleDateString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}),
  nx={giu:['hl ok','Có lãi ở cả hai nửa'],lo:['hl xau','Lỗ ở cả hai nửa'],khong_on:['hl','Không ổn định'],chua_du:['hl','Chưa đủ mẫu']},M=hocMoc(k),nam=new Date(M.tu).getFullYear();
 const dai=r.dai,dt=dai&&dai.truoc,dh=!dai?'':`<div class="hocr"><b>Các năm trước quãng này (${dai.tu_nam}–${dt.den_nam})</b>`
   +`<span>${dt.n} lệnh · có lãi ${pc(dt.ty_le)} · <i class="${mau(dt.usd_tb)}">${sg(dt.usd_tb)} USD mỗi lệnh</i> · ${dt.nam_lai}/${dt.so_nam} năm có lãi</span>`
   +(p.co&&dai.theo[p.huong]&&dai.theo[p.huong].truoc.n?`<span>Riêng chiều ${p.huong==='MUA'?'MUA':'BÁN'}: ${dai.theo[p.huong].truoc.n} lệnh, ${sg(dai.theo[p.huong].truoc.usd_tb)} USD mỗi lệnh</span>`:'')
   +(p.co&&dai.theo[p.huong]?`<span class="${dai.theo[p.huong].dat?'hl ok':'hl xau'}">Kỷ luật xét cả dòng này: chiều ${p.huong==='MUA'?'MUA':'BÁN'} ở các năm trước ${dai.theo[p.huong].dat?'có lãi':'không có lãi (hoặc chưa đủ 30 lệnh), nên Kỷ luật đứng ngoài'}</span>`:'')
   +`<span>USD mỗi lệnh theo năm: ${dai.theo_nam.map(x=>x[0]+' '+sg(x[3])).join(' · ')}</span>`
   +`<span class="${dt.usd_tb>0?'hl ok':'hl xau'}">${dt.usd_tb>0?'Các năm trước cũng có lãi':dai.sau.usd_tb>0?'Các năm trước không có lãi: phần lãi nằm ở quãng gần đây':'Các năm trước không có lãi, và quãng gần đây cũng không'}</span>`
   +(k==='dinh_day'?'<span>Luật này đặt dừng lỗ theo biên độ lúc đó (ATR), nên các năm cũ so được với hiện nay. Tham số của luật được chọn trên dữ liệu năm 2026, nên các năm trước đó là dữ liệu luật chưa từng thấy.</span></div>'
     :'<span>Mức chốt lời và dừng lỗ của luật này là số giá cố định, nên ở những năm giá vàng thấp hơn nhiều thì cùng một khoảng giá có nghĩa khác. Coi dòng này là tham khảo, không phải phép kiểm giống hệt.</span></div>');
 const mo=kcMo.has('hoc:'+p.ma)?' open':'',tm=r.theo_muc_tieu&&r.theo_muc_tieu.tat_ca,cuoi=dh+`<p class="why" style="margin:6px 0">${tm&&tm.n?`Nếu chốt ở mục tiêu lý thuyết thay cho 2R: ${tm.n} lệnh, có lãi ${pc(tm.ty_le)}, ${sg(tm.usd_tb)} USD mỗi lệnh. `:''}${HOC.ghi_chu?esc(HOC.ghi_chu)+' ':''}Dữ liệu ${ng(M.tu)} – ${ng(M.den)}. Nửa học là 70% đầu (tới ${ng(M.cat)}), nửa kiểm là 30% cuối. Một bối cảnh chỉ được coi là giữ được khi có lãi ở cả hai nửa và mỗi nửa đủ 30 lệnh. Đây là đếm lại quá khứ mà dự án đã nhìn thấy, không phải dự báo.</p></details>`;
 if(!p.co){const s=r.tat_ca;return `<details class="kc" data-ma="hoc:${p.ma}"${mo}><summary><b>Từ ${nam}:</b> ${s.n} lệnh cả hai chiều · có lãi ${pc(s.ty_le)} · <span class="${mau(s.usd_tb)}">${sg(s.usd_tb)} USD mỗi lệnh</span></summary>`+cuoi}
 const ch=p.huong==='MUA'?'MUA':'BÁN',ks=[[p.huong,'Cùng chiều '+ch],[p.huong+'|'+bc.phien,'Cùng chiều và phiên '+bc.phien]];
 if(bc.bien_do)ks.push([p.huong+'|'+bc.phien+'|'+bc.bien_do,'Cùng chiều, phiên '+bc.phien+', biên độ '+bc.bien_do]);
 const co=ks.map(([key,nhan])=>[nhan,r.theo[key]]),chon=[...co].reverse().find(([,s])=>s&&s.nhan_xet!=='chua_du')||co[0],sc=chon[1];
 let h=`<details class="kc" data-ma="hoc:${p.ma}"${mo}><summary><b>Từ ${nam}, bối cảnh giống lúc này:</b> ${sc?`<span class="${nx[sc.nhan_xet][0]}">${nx[sc.nhan_xet][1]}</span> (${esc(chon[0])}, ${sc.n} lệnh)`:'chưa có lệnh '+ch+' nào'}</summary>`
  +`<small>Lúc này: phiên ${esc(bc.phien||'—')}, biên độ ${esc(bc.bien_do||'chưa rõ')}${bc.bien_do_ty_le!=null?' (ATR H1 bằng '+f2(bc.bien_do_ty_le)+' lần mức thường)':''}</small>`;
 for(const[nhan,s]of co){h+=`<div class="hocr"><b>${esc(nhan)}</b>`;
  if(!s){h+='<span>Chưa có lệnh nào trong dữ liệu.</span></div>';continue}
  h+=`<span>${s.n} lệnh · có lãi ${pc(s.ty_le)} · <i class="${mau(s.usd_tb)}">${sg(s.usd_tb)} USD mỗi lệnh</i></span>`
   +`<span>Nửa học: ${s.hoc.n} lệnh${s.hoc.n?', '+sg(s.hoc.usd_tb)+' USD mỗi lệnh':''} · Nửa kiểm: ${s.kiem.n} lệnh${s.kiem.n?', '+sg(s.kiem.usd_tb)+' USD mỗi lệnh':''}</span>`
   +`<span class="${nx[s.nhan_xet][0]}">${nx[s.nhan_xet][1]}</span></div>`}
 return h+cuoi}
async function hocTai(){clearTimeout(hocCho);const ma0=ma;try{const r=await fetch('/api/hoc'+(ma?'?ma='+encodeURIComponent(ma):''),{cache:'no-store'});const j=await r.json();if(ma0!==ma)return;
  if(j.san_sang||!j.dang_tinh){HOC=j;if(!j.ma)dlTai();if(PTR&&!PTB.hidden)ptVe();dvKiem()}else hocCho=setTimeout(hocTai,3000)}
 catch(e){if(ma0!==ma)return;HOC={san_sang:false,loi:[e.message]};if(PTR&&!PTB.hidden)ptVe()}}
// kiểm trên giá mới (so_cong_khai/do_lai.py): các luật chốt ngày 24/11/2026 chạy lại trên giá từ 25/11/2026, kết luận theo luật đã đăng ký
let DL=null;async function dlTai(){try{const r=await fetch('/api/do-lai',{cache:'no-store'});if(r.ok){DL=await r.json();if(PTR&&!PTB.hidden)ptVe()}}catch(e){}}
const dlCua=k=>{if(!DL||!DL.co_the||!DL.muc)return null;const c=DL.muc.filter(x=>x.ma===k);return c.find(x=>/L6/.test(x.nhom||''))||c[0]||null},
 dlTxt=k=>{const x=dlCua(k);if(!x)return'';const mau=x.ket==='co_lai'?'gain':(x.ket==='lo_ro'||x.kem_ky_vong)?'loss':'';return `<small>giá mới: ${x.n} lệnh · <i class="${mau}">${esc(x.ket_ten||'')}${x.kem_ky_vong?', kém kỳ vọng rõ':''}</i></small>`};
function dlHtml(){if(!DL||!DL.co_the||!DL.muc||!DL.muc.length)return'';const g=DL.muc.filter(x=>x.ma);if(!g.length)return'';
 return `<p class="why" style="margin:6px 0"><b>Kiểm trên giá mới.</b> Chạy lại nguyên trạng các luật đã chốt trên giá từ 25/11/2026, phần chưa phép đo nào nhìn thấy${DL.luc?` (đo lúc ${vn(Date.parse(DL.luc)/1000)}, ${DL.so_ngay} ngày giá mới)`:''}: `+g.map(x=>`${esc(x.ten)}${/L6/.test(x.nhom||'')?' (có L6, tính từ 26/11)':''}: ${x.n} lệnh, ${esc(x.ket_ten||'')}${x.kem_ky_vong?', kém kỳ vọng rõ':''}`).join('; ')+`. Dưới 30 lệnh thì chưa kết luận; từ 30 lệnh kết luận theo khoảng tin cậy 90% của lãi lỗ mỗi lệnh. Tự đo lại mỗi tháng một lần; luật không được chỉnh theo số này.`+(DL.dang?' Đang đo lại…':` <button type="button" class="ictb dlb">Đo lại ngay</button>`)+(DL.loi?` <span class="stale">Lần đo gần nhất lỗi: ${esc(DL.loi)}</span>`:'')+'</p>'}
function phPlan(f){return{ma:'phieu:'+f.ma,ph:1,nhom:'pp',chip:(PTR.phuong_phap.find(x=>x.ma===f.ma)||{}).chip||f.ma,ten:'Phiếu · '+f.ten,huong:f.huong,vao:f.vao,sl:f.sl,tp:f.tp,rr:f.rr,vung:f.vung,hieu_luc:f.trang_thai==='con_hieu_luc',nen:f.nen,rui_ro_gia:f.rui_ro_gia,kieu:f.ten_loai,cu:f.vao_luc==='tin_hieu',kc:f.ket_cuc}}
function phBam(ma){const q=(PTR?[...(PTR.phuong_phap||[]),...(PTR.phuong_an||[])]:[]).find(x=>x.phieu&&x.phieu.ma===ma);if(!q||!q.phieu)return;plan=plan&&plan.ma==='phieu:'+q.phieu.ma?null:phPlan(q.phieu);planTat=plan?0:1;view.off=0;if(!PTB.hidden)ptVe();plH='';dvVe();draw()}
const PH_TT={con_hieu_luc:['ok','Đặt được lúc này'],bi_loc:['xau','Bộ lọc loại tín hiệu'],da_khop:['','Lệnh chờ đã khớp'],da_huy:['xau','Đã hủy'],het_han:['','Hết hạn'],qua_tre:['','Quá hạn vào ngay'],da_qua:['','Giá đã qua mức chờ'],rui_ro:['xau','Dừng lỗ ngoài khoảng']};
function phKc(f,t){return f.ket_cuc==='sl'?['xau','Đã qua · giá đã chạm dừng lỗ']:f.ket_cuc==='tp'?['','Đã qua · giá đã chạm chốt 2R']:t}
function phNgan(ds){const fs=ds.filter(x=>x.phieu).map(x=>x.phieu).sort((a,b)=>(a.trang_thai==='con_hieu_luc'?0:1)-(b.trang_thai==='con_hieu_luc'?0:1)||a.tuoi_phut-b.tuoi_phut).slice(0,3);if(!fs.length)return'';
 return'<div class="phn"><b class="phnt">Phiếu vào lệnh theo số đo</b><small class="phnc">công thức đã đo trên 11 năm; chưa công thức nào có lãi rõ ràng</small>'+fs.map(f=>{const t=phKc(f,PH_TT[f.trang_thai]||['',f.trang_thai]),ve=!!(plan&&plan.ma==='phieu:'+f.ma),mua=f.huong==='MUA';
  return`<div class="phr${f.trang_thai==='con_hieu_luc'?' song':''}"><div class="phh"><span class="dir ${mua?'up':'dn'}">${mua?'▲ MUA':'▼ BÁN'}</span><b>${esc(f.ten)}</b><span class="hl ${t[0]}">${t[1]}</span></div><small>${esc(f.ten_loai)}${f.con_phut!=null?' · còn '+f.con_phut+' phút':' · tín hiệu cách đây '+f.tuoi_phut+' phút'}</small>`
   +`<div class="phg"><span>${f.vao_luc==='tin_hieu'?'Vào lúc tín hiệu':'Vào'} <b>${fp(f.vao)}</b></span><span>Dừng lỗ <b class="loss">${fp(f.sl)}</b></span><span>Chốt 2R <b class="gain">${fp(f.tp[1])}</b></span><button type="button" class="ictb vph" data-ma="${esc(f.ma)}" aria-pressed="${ve}">${ve?'Đang vẽ':'Vẽ lên biểu đồ'}</button></div></div>`}).join('')+'</div>'}
function phHtml(p){const f=p.phieu;if(!f)return'';const TT={con_hieu_luc:['ok','Đặt được lúc này'],bi_loc:['xau','Bộ lọc loại tín hiệu này'],da_khop:['','Lệnh chờ đã khớp'],da_huy:['xau','Đã hủy: giá chạm dừng lỗ trước khi khớp'],het_han:['','Hết hạn 4 giờ'],qua_tre:['','Đã quá hạn vào ngay'],da_qua:['','Giá đã qua mức chờ lúc tín hiệu đến'],rui_ro:['xau','Khoảng dừng lỗ ngoài 0,5–3 ATR']}[f.trang_thai]||['',f.trang_thai],
 mua=f.huong==='MUA',von=rk.von>0?rk.von:0,lo=f.rui_ro_gia,so=v=>v==null?'—':(v>0?'+':'−')+Math.abs(v).toFixed(3).replace('.',','),pc=v=>v==null?'—':String(v).replace('.',',')+'%',ve=!!(plan&&plan.ma==='phieu:'+f.ma),
 hg=x=>`<span>${x.n.toLocaleString('vi-VN')}</span><span>${pc(x.khop_pct)}</span><span>${pc(x.thang)}</span><span class="${x.r_tb>0?'gain':'loss'}">${so(x.r_tb)}R</span><span>${x.pf==null?'—':String(x.pf).replace('.',',')}</span><span>${String(x.dd).replace('.',',')}R</span>`;
 let h=`<div class="ph"><div class="hd"><b>Phiếu vào lệnh theo số đo</b><small>đo ngày ${esc(f.ngay_do)} · không thay luật gốc ở trên</small></div><div><span class="dir ${mua?'up':'dn'}">${mua?'▲ MUA':'▼ BÁN'}</span> <span class="hl ${phKc(f,TT)[0]}">${phKc(f,TT)[1]}</span></div>`
  +(f.loc_hong&&f.loc_hong.length?`<p class="why" style="margin:4px 0"><b>Điều kiện chưa đạt:</b> ${esc(f.loc_hong.join('; '))}.</p>`:'')
  +`<div class="lv"><span>Loại lệnh</span><b>${esc(f.ten_loai)}</b><i>${f.con_phut!=null?'còn '+f.con_phut+' phút':'tín hiệu cách đây '+f.tuoi_phut+' phút'}</i>`
  +`<span>Giá vào</span><b>${fp(f.vao)}</b><i>${f.vao_luc==='tin_hieu'?'giá lúc tín hiệu đến, không phải giá hiện tại':f.vung?'vùng '+fp(Math.min(...f.vung))+' – '+fp(Math.max(...f.vung)):f.loai==='tt'?'giá hiện tại':''}</i>`
  +`<span>Dừng lỗ</span><b class="loss">${fp(f.sl)}</b><i>cách ${fp(f.rui_ro_gia)} giá</i>`
  +f.tp.map((t,j)=>`<span>Chốt lời ${j+1}</span><b class="gain">${fp(t)}</b><i>${f2(f.rr[j])}R${j?' · mức dùng để đo':' · tham khảo'}</i>`).join('')+'</div>'
  +`<p class="why" style="margin:4px 0">${esc(f.huy)}</p>`
  +`<p class="why" style="margin:4px 0">Khối lượng: ở 0,01 lot lỗ ${f2(lo)} USD nếu chạm dừng lỗ${von?' ('+f2(lo/von*100)+'% của vốn '+f2(von)+' USD)':''}. ${von&&rk.rr>0?(Math.floor(von*rk.rr/100/lo+1e-9)>=1?`Với mức rủi ro ${f2(rk.rr)}% bạn nhập ở ô tính khối lượng: tối đa ${(Math.floor(von*rk.rr/100/lo+1e-9)*0.01).toFixed(2).replace('.',',')} lot.`:`Mức rủi ro ${f2(rk.rr)}% bạn nhập không đủ cho 0,01 lot của phiếu này.`):'Nhập vốn và % rủi ro ở ô tính khối lượng để trang tính số lot.'}</p>`
  +'<div class="phdk">'+f.dieu_kien.map(d=>`<span class="${d.dat?'dat':'hong'}" title="${d.bat_buoc?'Bộ lọc này đã qua cổng đo nên là điều kiện bắt buộc của phiếu':'Chỉ để tham khảo: bộ lọc này không qua cổng đo cho phương pháp này'}">${d.dat?'✓':'✗'} ${esc(d.ten)}${d.bat_buoc?' (bắt buộc)':''}</span>`).join('')+'</div>'
  +(f.khac_luat_goc.length?`<p class="why" style="margin:4px 0"><b>Khác luật gốc:</b> ${esc(f.khac_luat_goc.join('; '))}.</p>`:'<p class="why" style="margin:4px 0">Kiểu vào giống luật gốc.</p>');
 if(f.so_do){const g=f.so_do.goc,q=f.so_do.phieu;h+=`<div class="phb"><b></b><b>Lệnh</b><b>Khớp</b><b>Thắng</b><b>Mỗi lệnh</b><b>PF</b><b>Sụt giảm</b>`
   +`<span>Luật gốc · 2015–${f.so_do.cat_nam-1}</span>${hg(g.chinh)}<span>Phiếu · 2015–${f.so_do.cat_nam-1}</span>${hg(q.chinh)}<span>Luật gốc · từ ${f.so_do.cat_nam}</span>${hg(g.kiem)}<span>Phiếu · từ ${f.so_do.cat_nam}</span>${hg(q.kiem)}</div>`
   +`<p class="why" style="margin:4px 0">Số đo trên vàng, mỗi tín hiệu chấm riêng, đã trừ spread của từng nến, trượt giá lúc tin và phí qua đêm. Công thức được chọn trên 2015–${f.so_do.cat_nam-1} và xác nhận trên phần từ ${f.so_do.cat_nam}; tổng cộng ${f.so_do.so_phep_so} phép so đã được làm cho tám phương pháp, nên một phần cải thiện có thể chỉ do may. ${q.chinh.r_tb<0?'Trên phần 2015–'+(f.so_do.cat_nam-1)+' phiếu này vẫn lỗ.':''} Phiếu ghi kết quả đo, không phải lời khuyên vào lệnh.</p>`}
 return h+`<button type="button" class="vph" data-ma="${esc(f.ma)}" aria-pressed="${ve}">${ve?'Đang vẽ phiếu trên biểu đồ':'Vẽ phiếu lên biểu đồ'}</button></div>`}
function kcHtml(p){if(PTR&&PTR.khac_vang)return hocHtml(p);       // mã khác vàng: chỉ có phần đo trên nến của chính mã đó
 return (p.nhom==='pp'?'':kcHtml0(p))+hocHtml(p)}
// --- đánh giá một phương án theo bằng chứng từ dữ liệu nhiều năm, và chọn phương án có bằng chứng tốt nhất
const ptDs=()=>PTR?[...(PTR.phuong_an||[]),...(PTR.phuong_phap||[])]:[],ppKhoa=p=>p.nhom==='pp'?(p.chip||p.ma):'luat',
 NX={giu:['hl ok','Có lãi ở cả hai nửa dữ liệu'],lo:['hl xau','Lỗ ở cả hai nửa dữ liệu'],khong_on:['hl','Không ổn định giữa hai nửa'],chua_du:['hl','Chưa đủ mẫu']};
function diem(p){if(!p.co||!PTR||!HOC||!HOC.san_sang)return null;const r=HOC.luat[p.ma.split(':')[0]],bc=PTR.boi_canh||{};if(!r)return null;
 const ks=[p.huong,p.huong+'|'+bc.phien];if(bc.bien_do)ks.push(p.huong+'|'+bc.phien+'|'+bc.bien_do);
 const co=ks.map(k=>r.theo[k]).filter(Boolean),s=[...co].reverse().find(x=>x.nhan_xet!=='chua_du')||co[0];return s?{ma:s.nhan_xet,s}:{ma:'chua_du',s:null}}
function daiDat(p){const r=HOC&&HOC.san_sang&&HOC.luat&&HOC.luat[p.ma.split(':')[0]],d=r&&r.dai;if(!d)return true;const t=d.theo&&d.theo[p.huong];return!!(t&&t.dat)}      // luật có số đo các năm trước quãng chọn: chiều lệnh này ở các năm đó cũng phải có lãi
function totNhat(){let chon=null;for(const p of ptDs()){if(!bat(ppKhoa(p))||!p.co||!p.hieu_luc)continue;const d=diem(p);if(!d||d.ma!=='giu'||!daiDat(p))continue;
  const v=d.s.kiem.usd_tb/(p.rui_ro_gia||1);if(!chon||v>chon.v)chon={p,d,v}}return chon}
function kcHtml0(p){const k=p.ma.split(':')[0],dau='<div class="kc"><b>Kiểm chứng lịch sử</b>';
 if(!KC)return dau+'<p class="why">Đang chạy lại luật trên kho nến 1 phút, khoảng 10 giây…</p></div>';
 if(!KC.san_sang)return dau+`<p class="stale">Không chạy lại được: ${esc((KC.loi||[]).join('; ')||'chưa rõ lý do')}</p></div>`;
 const r=KC.luat[k];if(!r)return dau+`<p class="stale">Không chạy lại được luật này. ${esc((KC.loi||[]).filter(e=>e.startsWith(k)).join('; '))}</p></div>`;
 const s=p.co?r[p.huong]:r.tat_ca,ch=p.co?(p.huong==='MUA'?'MUA':'BÁN'):'cả hai chiều',pc=v=>v.toFixed(1).replace('.',',')+'%',sg=v=>(v>0?'+':v<0?'−':'')+f2(Math.abs(v)),mau=v=>v>0?'gain':'loss';
 const tomtat=s.n?`${s.n} lệnh ${ch} · có lãi ${pc(s.ty_le)} · <span class="${mau(s.usd_tb)}">${sg(s.usd_tb)} USD mỗi lệnh</span>`:`luật chưa ra lệnh ${ch} nào`;
 let h=`<details class="kc" data-ma="${p.ma}"${kcMo.has(p.ma)||kcHien===k?' open':''}><summary><b>Kiểm chứng ${KC.so_ngay} ngày:</b> ${tomtat}</summary><small>${vn(Date.parse(KC.tu)/1000,1)} – ${vn(Date.parse(KC.den)/1000,1)} · chạy lại luật trên nến 1 phút</small>`;
 if(!s.n)h+=`<p class="why">Trong quãng này luật chưa ra lệnh ${ch} nào.</p>`;
 else{h+=kv('Số lần luật ra lệnh '+ch,s.n)+kv('Lệnh có lãi',s.thang+' / '+s.n+' ('+pc(s.ty_le)+')');
  if(s.tp1!=null)h+=kv('Chạm TP1 · TP2',pc(s.tp1)+' · '+pc(s.tp2))+kv('Chạm SL khi chưa có TP nào',pc(s.sl_tron));
  if(r.hoa_von!=null)h+=kv('Tỷ lệ thắng cần để hòa vốn',pc(r.hoa_von));
  h+=kv('Trung bình mỗi lệnh (0,01 lot)',`<span class="${mau(s.usd_tb)}">${sg(s.usd_tb)} USD</span>`)+kv('Tổng cả quãng',`<span class="${mau(s.tong)}">${sg(s.tong)} USD</span>`)
   +kv('Chuỗi không lãi dài nhất',s.chuoi_thua+' lệnh');
  if(p.co&&r.tat_ca.n>s.n)h+=`<p class="why" style="margin:6px 0">Cả hai chiều: ${r.tat_ca.n} lệnh, có lãi ${pc(r.tat_ca.ty_le)}, trung bình ${sg(r.tat_ca.usd_tb)} USD mỗi lệnh.</p>`;
  h+='<div class="kcl">'+s.gan_day.map(x=>`<span>${vn(Date.parse(x.t)/1000)}</span><span>${x.huong==='MUA'?'MUA':'BÁN'} ${f2(x.vao)}</span><span>${esc(x.ket)}</span><b class="${mau(x.usd)}">${sg(x.usd)}</b>`).join('')+'</div>';
  if(s.n<30)h+=`<p class="stale">Mẫu nhỏ: ${s.n} lệnh chưa đủ để kết luận điều gì.</p>`}
 if(p.ma==='bot:xu_huong')h+='<p class="why" style="margin:6px 0">Kiểu vào không chờ nến chưa có phép chạy lại riêng. Số trên là của kiểu nến tín hiệu, cùng luật.</p>';
 h+=`<p class="why" style="margin:6px 0">${esc(r.cach)} Spread cố định ${f2(KC.spread)}. Trong quãng này giá đi từ ${f2(KC.gia_dau)} tới ${f2(KC.gia_cuoi)} (${(KC.doi_pct>0?'+':'−')+pc(Math.abs(KC.doi_pct))}). ${k!=='dinh_day'&&Math.abs(KC.doi_pct)>=10?'Giá đi mạnh một chiều là điều kiện thuận cho luật theo xu hướng; số này không đại diện cho lúc thị trường đi ngang. ':''}Dự án đã nhìn thấy dữ liệu này nên đây không phải kiểm ngoài mẫu.</p>`;
 return h+`<button type="button" class="kcb" data-k="${k}" aria-pressed="${kcHien===k}">${kcHien===k?'Đang hiện các lần trước trên biểu đồ':'Hiện các lần trước trên biểu đồ'}</button>`
  +(kcHien===k?'<p class="why" style="margin:6px 0">▲ lệnh MUA, ▼ lệnh BÁN, đặt ở giá vào. Xanh là lệnh có lãi, đỏ là lệnh lỗ. Kéo biểu đồ lùi lại hoặc thu nhỏ để xem.</p>':'')+'</details>'}
async function kcTai(){clearTimeout(kcCho);try{const r=await fetch('/api/kiem-chung',{cache:'no-store'});const j=await r.json();
  if(j.san_sang||!j.dang_tinh){KC=j;if(PTR&&!PTB.hidden)ptVe();draw()}else kcCho=setTimeout(kcTai,2000)}
 catch(e){KC={san_sang:false,loi:[e.message]};if(PTR&&!PTB.hidden)ptVe()}}
// bảng lệnh tổng hợp: mọi phương án đang bật trong một bảng để so sánh một lần nhìn: hướng, giá vào, dừng lỗ, hai mức chốt lời kèm R,
// số đo nhiều năm (tỷ lệ có lãi · lãi lỗ trung bình mỗi lệnh) và nhận xét bằng chứng. Xếp: còn hiệu lực trước, rồi có điều kiện, rồi theo số đo.
let blDong=false;
// điểm khớp quá khứ (qua_khop.py): DSR = xác suất lợi thế là thật sau khi trừ hao số cấu hình đã thử; PBO = xác suất cấu hình đứng đầu chỉ là may
const QK=()=>HOC&&HOC.san_sang&&HOC.qua_khop,dsrCua=k=>{const q=QK(),c=q&&q.dsr&&q.dsr.cot&&q.dsr.cot[k];return c&&c.dsr!=null?c.dsr:null},
 ciTxt=c=>c.map(v=>`<i class="${c[0]>0?'gain':c[1]<0?'loss':''}">${(v>0?'+':v<0?'−':'')+f2(Math.abs(v))}</i>`).join(' … '),
 kySvg=k=>{const d=k.ds,m=Math.max(1e-9,...d.map(r=>Math.abs(r[4]))),w=Math.max(3,Math.min(7,Math.floor(84/d.length))),H=18,g=H/2,W=d.length*w;
  return `<svg class="kys" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true"><line x1="0" x2="${W}" y1="${g}" y2="${g}" style="stroke:var(--line)"/>`
   +d.map((r,i)=>{const h=Math.max(1,Math.abs(r[4])/m*(g-1));return `<rect x="${i*w+.5}" y="${r[4]>0?g-h:g}" width="${w-1}" height="${h}" style="fill:var(--${r[4]>0?'gain':'loss'});opacity:${r[1]<10?.35:1}"><title>${r[0]}: ${(r[4]>0?'+':r[4]<0?'−':'')+f2(Math.abs(r[4]))} USD · ${r[1]} lệnh</title></rect>`}).join('')+'</svg>'},
 kyNhan=k=>k.ky==='nam'?'năm có lãi':'tháng có lãi',
 kyTxt=s=>{const k=s&&s.theo_ky;return k&&k.so_ky?`<small>${kyNhan(k)} <i class="${k.ky_lai*2>k.so_ky?'gain':'loss'}">${k.ky_lai}/${k.so_ky}</i> ${kySvg(k)}</small>`:''},
 mpTxt=s=>s&&s.mo_phong?`<small>mô phỏng: mỗi lệnh ${ciTxt(s.mo_phong.tb_ci)} (95%) · sụt giảm xấu <i class="loss">−${f2(s.mo_phong.sut_p95)}</i></small>`:'',
 dsrTxt=v=>v==null?'—':`<i class="${v>=0.95?'gain':'loss'}">${(v*100).toFixed(v>=0.995||v<0.005?0:1).replace('.',',')}%</i>`;
function cvTxt(m){const c=m&&m.kiem_cheo,L=c&&c.loc;if(!L||L.top_r_tb==null)return'';const T=c.thuong,R=v=>(v>0?'+':'−')+f2(Math.abs(v))+'R',A=v=>String(v).replace('.',',');
 return ` Kiểm chéo ${L.k} phần theo thời gian, đã bỏ khỏi phần học các tín hiệu có kết quả chồng lên phần kiểm và ${A(L.ngay_cam)} ngày cấm ngay sau nó (purged CV, López de Prado 2018): nhóm 10% điểm cao nhất tốt hơn mặt bằng ở ${L.so_phan_hon}/${L.k} phần, có lãi ở ${L.so_phan_lai}/${L.k} phần, trung bình ${R(L.top_r_tb)} mỗi lệnh so với ${R(L.r_tb)}; AUC ${A(L.auc_tb)} (0,5 là đoán bừa).`
  +(T&&T.top_r_tb!=null?` Không bỏ phần chồng lấn thì ra ${R(T.top_r_tb)}, AUC ${A(T.auc_tb)}.`:'')}
function pboHtml(){const q=QK();if(!q)return'';const b=q.pbo,pc=v=>(v*100).toFixed(1).replace('.',',')+'%';
 return '<p class="why" style="margin:6px 0"><b>Khớp quá khứ.</b> Đã thử '+q.so_cau_hinh+' cấu hình (mỗi phương pháp với ba cách chốt lời, cộng các luật riêng). '
  +(b?`PBO = ${pc(b.pbo)}: tỷ lệ lần cấu hình đứng đầu ở phần dữ liệu dùng để chọn lại rơi xuống nửa dưới ở phần còn lại (CSCV, ${b.S} khối ${esc(q.ky)}, ${b.so_to_hop.toLocaleString('vi-VN')} cách chia). `
     +`Cấu hình được chọn đó lỗ ở phần còn lại trong ${pc(b.lo_khi_kiem)} số cách chia. PBO thấp chỉ nói thứ hạng ổn định, không nói cấu hình đứng đầu có lãi. `
    :`Chưa đo được PBO: ${esc(q.ly_do_pbo||'')}. `)
  +'Cột DSR: xác suất lợi thế của phương pháp là thật sau khi trừ hao số cấu hình đã thử; từ 95% trở lên mới đáng tin. Theo Bailey, Borwein, López de Prado và Zhu (2017), Bailey và López de Prado (2014).</p>'}
function phiTxt(){if(!HOC||!HOC.san_sang||HOC.spread==null)return'';const v=x=>String(x).replace('.',','),hh=+HOC.hoa_hong_lot||0;
 return ` Chi phí đã trừ: spread ${v(HOC.spread)}`+(HOC.ma?'':`, phí ước tính ${v(0.18)} mỗi lệnh`)+(hh?`, hoa hồng ${v(hh)} USD mỗi lot`:HOC.ma?', chưa trừ hoa hồng':'')+' (sửa ở <a href="/cai-dat">Cài đặt</a>).'}
function bangLenh(){const ds=ptDs().map((p,i)=>({p,i})).filter(({p})=>bat(ppKhoa(p)));if(!ds.length)return'';
 const sd=p=>{const r=HOC&&HOC.san_sang&&HOC.luat&&HOC.luat[p.ma.split(':')[0]];return r&&r.tat_ca&&r.tat_ca.n?r.tat_ca:null},
  hang=({p})=>[p.co&&p.hieu_luc?0:p.co?1:2,p.co?ppHang(p):3,-((sd(p)||{}).usd_tb??-1e9)],
  pc=v=>v==null?'—':v.toFixed(1).replace('.',',')+'%',sg=v=>v==null?'—':`<i class="${v>0?'gain':'loss'}">${(v>0?'+':'−')+f2(Math.abs(v))}</i>`,
  so=(s,k)=>(s?`<small>số đo: thắng <i class="${s.hoa_von==null?'':s.ty_le>s.hoa_von?'gain':'loss'}">${pc(s.ty_le)}</i>${s.hoa_von!=null?` · hòa vốn cần ${pc(s.hoa_von)}`:''}</small><small>${sg(s.usd_tb)} mỗi lệnh${s.lai_tb!=null&&s.lo_tb!=null?` · thắng TB ${sg(s.lai_tb)}, thua TB ${sg(-s.lo_tb)}`:''}</small>${s.sut_max!=null?`<small>sụt giảm lớn nhất <i class="loss">−${f2(s.sut_max)}</i> · thua liền tối đa ${s.chuoi_thua} lệnh</small>`:''}${mpTxt(s)}${kyTxt(s)}${dlTxt(k)}`:'<small>chưa có số đo</small>')+(QK()?`<small>lợi thế thật (DSR): ${dsrTxt(dsrCua(k))}</small>`:'');
 ds.sort((a,b)=>{const x=hang(a),y=hang(b);for(let k=0;k<3;k++)if(x[k]!==y[k])return x[k]-y[k];return 0});
 const co=ds.filter(x=>x.p.co),hl=co.filter(x=>x.p.hieu_luc);
 let h=`<details class="bl"${blDong?'':' open'}><summary><b>Bảng lệnh của mọi phương pháp</b> · ${co.length} có điều kiện, ${hl.length} còn hiệu lực</summary><div class="blw"><table class="blt">`
  +'<thead><tr><th>Phương pháp</th><th>Lệnh</th><th>Dừng lỗ</th><th>Chốt lời</th></tr></thead><tbody>';
 for(const{p,i}of ds){const s=sd(p),d=diem(p),ve=!!(plan&&plan.ma===p.ma);
  if(!p.co){h+=`<tr><td>${esc(p.ten)}<small>không có điều kiện</small>${so(s,p.ma.split(':')[0])}</td><td colspan="3" class="mo">${esc((p.vi_sao||'').slice(0,90))}${(p.vi_sao||'').length>90?'…':''}</td></tr>`;continue}
  const tp=p.tp||[],rr=p.rr||[],mua=p.huong==='MUA';
  h+=`<tr class="${p.hieu_luc?'hl1':''}${ve?' chon':''}"><td><b>${esc(p.ten)}</b><small>${p.hieu_luc?'Còn hiệu lực':'Chỉ để tham khảo'}${d?' · '+NX[d.ma][1]:''}</small>${so(s,p.ma.split(':')[0])}</td>`
   +`<td><span class="dir ${mua?'up':'dn'}">${mua?'▲ MUA':'▼ BÁN'}</span><small>vào ${fp(p.vao)}</small><button type="button" class="ve" data-i="${i}" aria-pressed="${ve}">${ve?'Đang vẽ':'Vẽ'}</button></td>`
   +`<td><b class="loss">${fp(p.sl)}</b><small>cách ${fp(p.rui_ro_gia!=null?p.rui_ro_gia:Math.abs(p.vao-p.sl))}</small></td>`
   +`<td>${tp.slice(0,2).map((t,j)=>`<b class="gain">${fp(t)}</b><small>${rr[j]!=null?f2(rr[j])+'R':'TP'+(j+1)}</small>`).join('')||'—'}</td>`
   +'</tr>'}
 return h+'</tbody></table></div><p class="why" style="margin:4px 0 8px">Số đo: tỷ lệ lệnh có lãi và lãi lỗ trung bình mỗi lệnh ('+esc((HOC&&HOC.don_vi)||'USD ở 0,01 lot')+'), chạy lại đúng quy tắc của phương pháp trên dữ liệu quá khứ; "—" là chưa có số đo. Hòa vốn cần = thua TB ÷ (thắng TB + thua TB): tỷ lệ thắng phải cao hơn mức này mới có lãi (xanh là cao hơn, đỏ là thấp hơn), nên tỷ lệ thắng cao mà thua TB lớn hơn nhiều thắng TB vẫn lỗ. Sụt giảm lớn nhất là mức lỗ cộng dồn từ đỉnh xuống đáy mà bạn phải chịu được nếu làm theo phương pháp.'+(ds.some(({p})=>(sd(p)||{}).mo_phong)?' Mô phỏng: xáo lại chuỗi lệnh quá khứ theo từng khối lệnh liền nhau hàng nghìn lần (block bootstrap); "mỗi lệnh 95%" là khoảng chứa lãi lỗ trung bình mỗi lệnh ở 95% số lần, cả khoảng trên 0 mới tách được lợi thế khỏi may; "sụt giảm xấu" là mức sụt chỉ 5% số lần vượt qua, thường sâu hơn con số đã xảy ra.':'')+(ds.some(({p})=>((sd(p)||{}).theo_ky||{}).so_ky)?' Năm (tháng) có lãi: trong các năm có ít nhất 10 lệnh, bao nhiêu năm tổng dương; các cột nhỏ là lãi lỗ từng năm, cột mờ là năm có dưới 10 lệnh. Lãi đến đều qua nhiều năm đáng tin hơn lãi chỉ nhờ một hai năm.':'')+phiTxt()+' Bấm "Vẽ" để hiện vùng vào, dừng lỗ và chốt lời trên biểu đồ. Kết quả quá khứ không bảo đảm tương lai; đây không phải lời khuyên đầu tư.</p></details>'}
function ptVe(){if(!PTR){PTB.hidden=true;return}const cuon=PTB.scrollTop;const b=PTR.boi_canh||{},x=b.xu_huong||{},dt=PTR.dong_thuan||{};
 let h='<button type="button" class="x" id="pt-x" aria-label="Đóng">Đóng</button><h3>Phân tích lúc '+vn(Date.parse(PTR.luc)/1000)+'</h3><p class="why" style="margin:-2px 0 8px">Tự cập nhật mỗi 15 giây khi có giá trực tiếp, mỗi phút khi không.'+(PTR.ms&&PTR.ms['Tổng']!=null?' Lần này máy tính xong trong '+(PTR.ms['Tổng']/1000).toFixed(2).replace('.',',')+' giây.':'')+'</p>';
 for(const c of PTR.canh_bao||[])h+=`<p class="stale">${esc(c)}</p>`;
 h+=kv('Giá Bid / Ask',fp(PTR.bid)+' / '+fp(PTR.ask))+kv('Xu hướng D1 · H4 · H1',[x.D1,x.H4,x.H1].map(v=>v>0?'tăng':v<0?'giảm':'ngang').join(' · '))
  +kv('ATR14 (M15)',fp(b.atr_m15))+kv('Kháng cự / hỗ trợ 2 giờ',fp(b.khang_cu)+' / '+fp(b.ho_tro));
 const z=b.vung||{};if(z.tren)h+=kv(esc(z.tren.loai)+' phía trên',fp(z.tren.duoi)+' – '+fp(z.tren.tren));if(z.duoi)h+=kv(esc(z.duoi.loai)+' phía dưới',fp(z.duoi.duoi)+' – '+fp(z.duoi.tren));
 if(b.tin&&b.tin.sap_toi)h+=kv('Tin USD mạnh kế tiếp',vn(Date.parse(b.tin.sap_toi)/1000));
 if(b.lien_thi_truong){const u=b.lien_thi_truong,ux=u.usd_xu_huong||{},c=v=>v>0?'mạnh lên':v<0?'yếu đi':'ngang';
  h+=kv('USD hôm nay (so với '+u.so_cap+' đồng tiền chính)',`<span class="${u.usd_ngay_pct>0?'gain':u.usd_ngay_pct<0?'loss':''}">${(u.usd_ngay_pct>0?'+':u.usd_ngay_pct<0?'−':'')+f2(Math.abs(u.usd_ngay_pct))}%</span>`)
   +kv('USD theo D1 · H4 · H1',[ux.D1,ux.H4,ux.H1].map(c).join(' · '))
   +'<p class="why" style="margin:6px 0 0">Liên thị trường: vàng thường đi ngược USD, nhưng không phải lúc nào cũng vậy. Phần này chỉ là bối cảnh, không ra điểm vào; lãi suất và lợi suất trái phiếu chưa có trong dữ liệu.</p>'}
 h+='<h3>Phương pháp phân tích</h3><div class="chips ppc">'+[['luat','Luật của bạn'],...(PTR.phuong_phap||[]).map(p=>[p.chip||p.ma,p.ten_ngan||p.ten])].filter((x,i,a)=>!(PTR.khac_vang&&x[0]==='luat')&&a.findIndex(y=>y[0]===x[0])===i)
  .map(([k,n])=>`<button type="button" class="chip" data-pp="${k}" aria-pressed="${bat(k)}"><i></i>${esc(n)}</button>`).join('')+'</div>';
 {const ds=ptDs().filter(p=>bat(ppKhoa(p))),co=ds.filter(p=>p.co),hl=co.filter(p=>p.hieu_luc),tn=totNhat();
  if(PTR.khac_vang&&HOC&&!HOC.san_sang)h+=`<p class="why">${co.length} phương pháp có điều kiện, ${hl.length} còn hiệu lực. Chưa đo được trên mã này: ${esc((HOC.loi||[]).join('; ')||'chưa rõ lý do')}.</p>`;
  else if(!HOC||!HOC.san_sang)h+=`<p class="why">${co.length} phương án có điều kiện, ${hl.length} còn hiệu lực. Đang tính bằng chứng từ dữ liệu quá khứ…</p>`;
  else if(tn)h+=`<p class="tn"><b>Bằng chứng tốt nhất lúc này: ${esc(tn.p.ten)}, ${tn.p.huong==='MUA'?'MUA':'BÁN'}.</b> Trong bối cảnh giống lúc này từ ${new Date(hocMoc(tn.p.ma.split(':')[0]).tu).getFullYear()}, phương án này có lãi ở cả nửa học lẫn nửa kiểm (${tn.d.s.n} lệnh, nửa kiểm ${f2(tn.d.s.kiem.usd_tb)} USD mỗi lệnh ở 0,01 lot). Đây là xếp hạng theo số liệu quá khứ, không phải dự báo.</p>`;
  else h+=`<p class="why">${co.length} phương án có điều kiện, ${hl.length} còn hiệu lực. <b>Chưa phương án nào vừa còn hiệu lực vừa có lãi ở cả hai nửa dữ liệu.</b></p>`}
 h+=bangLenh();
 if(HOC&&HOC.san_sang){const hg=Object.entries(HOC.luat).filter(([,r])=>r.r1&&r.r1.tat_ca.n&&r.tat_ca.n).map(([k,r])=>[((PTR.phuong_phap||[]).find(x=>x.ma===k)||{}).ten||k,r,k]).sort((a,b)=>b[1].tat_ca.usd_tb-a[1].tat_ca.usd_tb),
   pc=v=>v.toFixed(1).replace('.',',')+'%',sg=v=>`<i class="${v>0?'gain':'loss'}">${(v>0?'+':'−')+f2(Math.abs(v))}</i>`,mp=hg.some(x=>x[1].tat_ca.mo_phong);
  if(hg.length)h+=`<details class="kc" data-ma="xep-hang"${kcMo.has('xep-hang')?' open':''}><summary><b>Bảng xếp hạng phương pháp theo số đo</b> (từ ${new Date((hg[0][1].tu)||HOC.tu).getFullYear()}, ${esc(HOC.don_vi||'USD ở 0,01 lot')})</summary><div class="bxh${QK()?' dsr':''}"><b>Phương pháp</b><b>Lệnh</b><b>Chốt 1R</b><b>Chốt 2R</b>${QK()?'<b>DSR</b>':''}`
   +hg.map(([ten,r,k])=>`<span>${esc(ten)}</span><span>${r.tat_ca.n}</span><span>${pc(r.r1.tat_ca.ty_le)} · ${sg(r.r1.tat_ca.usd_tb)}</span><span>${pc(r.tat_ca.ty_le)} · ${sg(r.tat_ca.usd_tb)}${r.tat_ca.mo_phong?`<small class="ci">95%: ${ciTxt(r.tat_ca.mo_phong.tb_ci)}</small>`:''}${r.tat_ca.theo_ky&&r.tat_ca.theo_ky.so_ky?`<small class="ci">${kyNhan(r.tat_ca.theo_ky)} <i class="${r.tat_ca.theo_ky.ky_lai*2>r.tat_ca.theo_ky.so_ky?'gain':'loss'}">${r.tat_ca.theo_ky.ky_lai}/${r.tat_ca.theo_ky.so_ky}</i></small>`:''}</span>${QK()?`<span>${dsrTxt(dsrCua(k))}</span>`:''}`).join('')
   +'</div><p class="why" style="margin:6px 0">Mỗi ô: tỷ lệ lệnh có lãi và lãi lỗ trung bình mỗi lệnh. Chốt ở 1R cần thắng hơn 50% mới hòa vốn, chốt ở 2R cần hơn 33,3%; spread và phí làm ngưỡng thật cao hơn một chút. Xếp theo lãi lỗ trung bình khi chốt ở 2R. Thử nhiều phương pháp thì cái đứng đầu có thể chỉ là may.'+(mp?' Dòng 95% dưới ô chốt 2R: khoảng chứa lãi lỗ trung bình mỗi lệnh khi mô phỏng lại chuỗi lệnh hàng nghìn lần theo khối (block bootstrap, Künsch 1989); khoảng còn chứa 0 nghĩa là chưa tách được khỏi may, kể cả khi chỉ xét riêng phương pháp đó.':'')+(hg.some(x=>(x[1].tat_ca.theo_ky||{}).so_ky)?' Dòng "năm có lãi" đếm các năm có ít nhất 10 lệnh và tổng dương (mã khác vàng chưa đủ một năm dữ liệu nên đếm theo tháng).':'')+'</p>'+pboHtml()+dlHtml()+(PTR&&PTR.mo_hinh&&PTR.mo_hinh.san_sang&&cvTxt(PTR.mo_hinh)?'<p class="why" style="margin:6px 0"><b>Điểm mô hình (thử nghiệm).</b>'+cvTxt(PTR.mo_hinh)+' Mô hình chỉ xếp hạng điểm vào, chưa phải tín hiệu.</p>':'')+'</details>'}
 if(PTR.ict&&PTR.ict.du&&bat('ict')){const I=PTR.ict,dk=I.dieu_kien||[],dat=dk.filter(x=>x.dat===true).length,ps=(PTR.phuong_phap||[]).filter(p=>p.chip==='ict'&&p.co),hl=ps.find(p=>p.hieu_luc),p0=hl||ps[0],hg=v=>v==='MUA'?'MUA':'BÁN';
  h+='<h3>ICT/SMC: bản đồ và điều kiện lúc này</h3>'
   +(p0?`<p class="${hl?'tn':'why'}"><b>${hl?'Có điểm vào ICT còn hiệu lực':'Có điểm vào ICT, chỉ để tham khảo'}: lệnh chờ ${hg(p0.huong)} tại ${fp(p0.vao)}, dừng lỗ ${fp(p0.sl)}, chốt ${fp(p0.tp[p0.tp.length-1])}.</b> ${hl?'':esc((p0.vi_sao_het||[]).join(' '))} Đạt ${dat}/${dk.length} điều kiện. Chi tiết ở thẻ phương án bên dưới.</p>`
    :`<p class="why"><b>Chưa có điểm vào theo ICT.</b> Đạt ${dat}/${dk.length} điều kiện${I.huong_xet?' cho chiều '+hg(I.huong_xet):''}. Trang không ép ra lệnh khi điều kiện chưa đủ.</p>`)
   +'<div class="ictk">'+dk.map(x=>`<i class="${x.dat===true?'dat':x.dat===false?'chua':'kx'}">${x.dat===true?'✓':x.dat===false?'✗':'–'}</i><span><b>${esc(x.ten)}</b><br>${esc(x.chi_tiet)}</span>`).join('')+'</div>'
   +`<p class="why" style="margin:6px 0">${esc(I.ghi_chu||'')}</p>`+(I.kich_ban||[]).map(k=>`<p class="why" style="margin:4px 0">• ${esc(k)}</p>`).join('')
   +`<button type="button" class="ictb" aria-pressed="${!!ictVe}">${ictVe?'Đang vẽ bản đồ ICT trên biểu đồ':'Vẽ bản đồ ICT lên biểu đồ'}</button>`
   +(ictVe?`<p class="why" style="margin:6px 0">Trên biểu đồ: BSL và SSL (gạch tím) là thanh khoản trên và dưới; hộp đỏ, hộp xanh là khoảng trống giá (FVG) giảm, tăng gần giá nhất; BOS là phá cấu trúc cùng chiều, CHoCH là đổi chiều; dấu ✕ là chỗ giá quét thanh khoản; EQ 50%, PDH, PDL (chấm xám) là mức giữa biên độ 24 giờ và đỉnh, đáy hôm trước. <b>Rê chuột vào từng ghi chú để xem giải thích cụ thể.</b>${LW?'':' Bản đồ chỉ vẽ được trên lớp biểu đồ mới.'}</p>`:'')}
 if(PTR.khac_vang)h+=`<h3>${PTR.chia_se?'Về các phương pháp ở đây':'Vì sao không có luật của bạn'}</h3><p class="why">${esc(PTR.giai_thich)}</p>`;else if(bat('luat'))h+=`<h3>Các luật của bạn nói gì</h3><p class="why">${dt.MUA||0} phương án MUA, ${dt.BAN||0} phương án BÁN, ${dt.khong||0} luật không có điều kiện. Còn hiệu lực lúc này: ${PTR.con_hieu_luc||0}. Số phương án cùng chiều không làm một luật đáng tin hơn số đo của chính nó.</p>`;
 let daPP=0;ptDs().forEach((p,i)=>{if(!bat(ppKhoa(p)))return;if(p.nhom==='pp'&&!daPP){daPP=1;h+='<h3>Phương pháp tùy chọn</h3><p class="why">Quy tắc máy của các phương pháp phổ biến, không phải luật trong sổ của bạn và chưa từng chạy bóng.</p>'}
  const dg_=diem(p);h+=`<div class="pa${plan&&plan.ma===p.ma?' sel':''}"><div class="hd"><b>${esc(p.ten)}</b><small>${esc(p.truong_phai?p.truong_phai+' · '+p.kieu:p.kieu)}</small></div>`+(dg_?`<div style="margin:4px 0 0"><span class="${NX[dg_.ma][0]}">${NX[dg_.ma][1]}</span></div>`:'');
  if(!p.co){h+=`<p class="why" style="margin:6px 0 0"><b>Không có điều kiện.</b> ${esc(p.vi_sao)}</p>${phHtml(p)}${kcHtml(p)}</div>`;return}
  const von=rk.von>0?rk.von:0,lo01=p.rui_ro_gia;
  h+=`<div><span class="dir ${p.huong==='MUA'?'up':'dn'}">${p.huong==='MUA'?'▲ MUA':'▼ BÁN'}</span> <span class="hl${p.hieu_luc?' ok':''}">${p.hieu_luc?'Còn hiệu lực':'Chỉ để tham khảo'}</span></div>`
   +(p.hieu_luc?'':`<p class="why" style="margin:4px 0"><b>Luật thật không vào lệnh lúc này:</b> ${esc((p.vi_sao_het||[]).join(' '))}</p>`)+`<div class="lv"><span>Giá vào</span><b>${fp(p.vao)}</b><i>${p.vung?'vùng '+fp(Math.min(...p.vung))+' – '+fp(Math.max(...p.vung)):''}</i>`
   +`<span>Dừng lỗ</span><b class="loss">${fp(p.sl)}</b><i>cách ${fp(p.rui_ro_gia)} giá</i>`
   +p.tp.map((t,j)=>`<span>TP${p.tp.length>1?j+1:''}</span><b class="gain">${fp(t)}</b><i>${p.rr[j]!=null?f2(p.rr[j])+'R':''}</i>`).join('')+(p.muc_tieu?`<span>Mục tiêu lý thuyết</span><b>${fp(p.muc_tieu.gia)}</b><i>${f2(p.muc_tieu.r)}R</i>`:'')+'</div>'
   +`<p class="why" style="margin:4px 0">${esc(p.ly_do)}</p>${PTR.khac_vang?'<p class="why" style="margin:4px 0;display:none">':'<p class="why" style="margin:4px 0">'}Ở 0,01 lot: lỗ ${f2(lo01)} USD nếu chạm SL${von?' ('+f2(lo01/von*100)+'% của vốn '+f2(von)+' USD)':''}. ${von&&rk.rr>0?(Math.floor(von*rk.rr/100/lo01+1e-9)>=1?`Mức rủi ro ${f2(rk.rr)}% bạn đặt cho phép lỗ ${f2(von*rk.rr/100)} USD, tức tối đa ${(Math.floor(von*rk.rr/100/lo01+1e-9)*0.01).toFixed(2).replace('.',',')} lot.`:`Mức rủi ro ${f2(rk.rr)}% bạn đặt chỉ cho phép lỗ ${f2(von*rk.rr/100)} USD, không đủ cho 0,01 lot của phương án này.`):''}</p>`
   +(p.ghi_chu||[]).map(g=>`<p class="why" style="margin:4px 0">• ${esc(g)}</p>`).join('')
   +`<p class="why" style="margin:4px 0"><b>${p.nhom==='pp'?'Quy tắc:':'Số đo dài hạn (báo cáo của bạn):'}</b> ${esc(p.thong_ke)}</p><button type="button" class="ve" data-i="${i}" aria-pressed="${!!(plan&&plan.ma===p.ma)}">${plan&&plan.ma===p.ma?'Đang vẽ trên biểu đồ':'Vẽ lên biểu đồ'}</button>${phHtml(p)}${kcHtml(p)}</div>`});
 for(const e of PTR.loi||[])h+=`<p class="stale">${esc(e)}</p>`;
 h+=PTR.khac_vang?'<p class="why">Đây là số liệu mô tả thị trường tính trên nến đã đóng, không phải tín hiệu. Trang không đặt lệnh; đây không phải lời khuyên đầu tư.</p>':'<p class="why">Các mức giá trên là kết quả của những luật bạn đã viết, tính trên nến đã đóng và giá hiện có. Theo sổ của bạn, chưa luật nào được chứng minh có lãi. Trang không đặt lệnh; đây không phải lời khuyên đầu tư.</p>';
 PTB.innerHTML=h;PTB.hidden=false;PTB.scrollTop=cuon;$('#pt-x').addEventListener('click',()=>{PTB.hidden=true});
 PTB.querySelectorAll('.ppc .chip').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.pp;ppBat[k]=bat(k)?0:1;try{localStorage.setItem('so-pp',JSON.stringify(ppBat))}catch(e){}if(plan&&plan.ma!=='ai'&&!bat(ppKhoa(plan)))plan=null;ptVe();draw()}));
 PTB.querySelectorAll('.ictb').forEach(b=>b.addEventListener('click',()=>{ictVe=!ictVe;try{localStorage.setItem('so-ict',ictVe?'1':'0')}catch(e){}ptVe();draw()}));
 PTB.querySelectorAll('details.kc').forEach(d=>d.addEventListener('toggle',()=>{if(d.open)kcMo.add(d.dataset.ma);else kcMo.delete(d.dataset.ma)}));
 PTB.querySelector('details.bl')?.addEventListener('toggle',e=>{blDong=!e.target.open});
 PTB.querySelectorAll('.kcb').forEach(b=>b.addEventListener('click',()=>{kcHien=kcHien===b.dataset.k?null:b.dataset.k;ptVe();draw()}));
 PTB.querySelectorAll('.ve').forEach(b=>b.addEventListener('click',()=>{const p=ptDs()[+b.dataset.i];plan=plan&&plan.ma===p.ma?null:p;planTat=plan?0:1;view.off=0;ptVe();draw();if(plan&&hep()&&!fsOn())CP.scrollIntoView({behavior:'smooth',block:'start'})}));PTB.querySelectorAll('.vph').forEach(b=>b.addEventListener('click',()=>{phBam(b.dataset.ma);if(plan&&hep()&&!fsOn())CP.scrollIntoView({behavior:'smooth',block:'start'})}));dvVe()}
// --- báo khi một phương pháp đang bật có điểm vào còn hiệu lực. Chỉ báo trong trang; trang không đặt lệnh.
let DV=[],dvDa=new Map();try{dvDa=new Map(JSON.parse(sessionStorage.getItem('so-dv')||'[]'))}catch(e){}
// --- thanh chọn phương pháp và phiếu lệnh: bấm một phương pháp thì trang nêu điểm vào, dừng lỗ, chốt lời và mục tiêu theo lý thuyết của nó
const klDat=p=>{const d=diem(p),r=HOC&&HOC.san_sang&&HOC.luat&&HOC.luat[p.ma.split(':')[0]],c=r&&r.theo&&r.theo[p.huong];return!!(d&&d.ma==='giu'&&c&&c.nhan_xet==='giu'&&daiDat(p))},      // kỷ luật: cả chiều lệnh nói chung lẫn bối cảnh giống lúc này đều phải có lãi ở hai nửa
 ppNhom=k=>ptDs().filter(p=>k==='tat'?bat(ppKhoa(p)):ppKhoa(p)===k),
 ppHang=p=>{const d=diem(p);return!d?1:d.ma==='giu'?0:d.ma==='lo'?2:1},      // có lãi ở cả hai nửa xếp trước, lỗ ở cả hai nửa xếp sau cùng
 ppTot=(k,chiHL)=>{const ds=[...ppNhom(k)].sort((a,b)=>ppHang(a)-ppHang(b)),tn=k==='tat'?totNhat():null;return(tn&&tn.p)||ds.find(p=>p.hieu_luc)||(chiHL?null:ds.find(p=>p.co))||null};
let plKhoa='',plH='',plMo=false;
function plCach(){const e=$('#pl-cach');if(e&&D)e.textContent='cách giá hiện tại '+fp(Math.abs(+e.dataset.vao-(D.bid||D.candles[D.candles.length-1][4])))}
function dvVe(){const el=$('#dv');if(!el)return;if(!PTR){el.hidden=true;el.innerHTML='';plH='';return}
 const tabs=[['tat','Tất cả phương pháp'],['luat','Luật của bạn'],...(PTR.phuong_phap||[]).map(p=>[p.chip||p.ma,p.ten_ngan||p.ten])].filter((x,i,a)=>!(PTR.khac_vang&&x[0]==='luat')&&a.findIndex(y=>y[0]===x[0])===i);
 if(!tabs.some(t=>t[0]===ppChon))ppChon='tat';
 const tt=k=>{const ds=ppNhom(k);return ds.some(p=>p.hieu_luc)?'ok':ds.some(p=>p.co)?'tk':''},ttc={ok:', có điểm vào còn hiệu lực',tk:', có điểm vào để tham khảo','':''},nh=ppNhom(ppChon),
  p=(plan&&plan.ma!=='ai'&&nh.find(x=>x.co&&x.ma===plan.ma))||ppTot(ppChon),atr=PTR.boi_canh&&PTR.boi_canh.atr_m15,sg=v=>(v>0?'+':'−')+fp(Math.abs(v));
 let h='<div class="ppt" role="tablist" aria-label="Phương pháp phân tích">'+tabs.map(([k,n])=>`<button type="button" role="tab" class="ppx" data-k="${k}" aria-selected="${k===ppChon}" title="${esc(n+ttc[tt(k)])}"><i class="${tt(k)}"></i>${esc(n)}</button>`).join('')+`<button type="button" class="chip kl" aria-pressed="${kyLuat}" title="Kỷ luật: chỉ chấp nhận và chỉ báo điểm vào khi cả chiều lệnh của phương pháp lẫn bối cảnh giống lúc này đều có lãi ở nửa học và nửa kiểm; với luật trong sổ, các năm trước quãng này cũng phải có lãi"><i></i>Kỷ luật</button>${PTR.mo_hinh&&PTR.mo_hinh.san_sang?`<button type="button" class="chip mhl" aria-pressed="${mhLoc}" title="Chỉ báo điểm vào có điểm mô hình từ 90 (nhóm 10% cao nhất). Chỉ có cho vàng; thử nghiệm."><i></i>Mô hình ≥ 90</button>`:''}</div>`;
 if(p){const d=diem(p),len=p.huong==='MUA',ve=!!(plan&&plan.ma===p.ma),mt=p.muc_tieu,rm=HOC&&HOC.san_sang&&HOC.luat&&HOC.luat[p.ma.split(':')[0]],tm=rm&&rm.theo_muc_tieu&&rm.theo_muc_tieu.tat_ca,s2=rm&&rm.theo&&rm.theo[p.huong],s1=rm&&rm.r1&&rm.r1[p.huong],pcx=v=>v.toFixed(1).replace('.',','),tn2=v=>(v>0?'+':'−')+f2(Math.abs(v)),kl=klDat(p),bt=PTR.mo_hinh&&PTR.mo_hinh.bac_thang&&(PTR.mo_hinh.bac_thang[p.ma]||{})[p.huong],soR=v=>f2(v).replace(/,?0+$/,''),
   soDo=p.nhom==='pp'&&s2&&s2.n?`<p class="why">Số đo chiều ${len?'MUA':'BÁN'} của phương pháp này: `+(s1&&s1.n?`chốt ở 1R thắng ${pcx(s1.ty_le)}% (hòa vốn cần hơn ${s1.hoa_von!=null?pcx(s1.hoa_von):'50'}%), ${tn2(s1.usd_tb)} USD mỗi lệnh; `:'')+`chốt ở 2R thắng ${pcx(s2.ty_le)}% (hòa vốn cần hơn ${s2.hoa_von!=null?pcx(s2.hoa_von):'33,3'}%), ${tn2(s2.usd_tb)} USD mỗi lệnh, trên ${s2.n} lệnh.</p>`:'';
  h+=`<div class="pl"><div class="plh"><span class="dir ${len?'up':'dn'}">${len?'▲ MUA':'▼ BÁN'}</span><b>${esc(p.ten)}</b><span class="hl${p.hieu_luc?' ok':''}">${p.hieu_luc?'Còn hiệu lực':'Chỉ để tham khảo'}</span>`+(kyLuat?`<span class="hl ${kl?'ok':'xau'}">${kl?'Kỷ luật: đạt':'Kỷ luật: đứng ngoài'}</span>`:'')+(p.mo_hinh?`<span class="hl${p.mo_hinh.hang>=90?' ok':''}" title="Điểm mô hình (thử nghiệm): xếp hạng so với các tín hiệu từ 2015">Mô hình ${p.mo_hinh.hang}/100</span>`:'')
   +(d?`<span class="${NX[d.ma][0]}">${NX[d.ma][1]}${d.s?` · ${d.s.n} lệnh, có lãi ${d.s.ty_le.toFixed(1).replace('.',',')}%`:''}</span>`:'')+`<small>${esc(p.kieu||'')}</small></div><div class="plg">`
   +`<div><small>Vào lệnh</small><b>${fp(p.vao)}</b><i id="pl-cach" data-vao="${p.vao}"></i></div>`
   +`<div class="sl"><small>Dừng lỗ</small><b>${fp(p.sl)}</b><i>${sg(-p.rui_ro_gia)}${atr?' · '+f2(p.rui_ro_gia/atr)+' ATR':''}</i></div>`
   +p.tp.slice(0,3).map((t,j)=>`<div class="tp"><small>Chốt lời ${p.tp.length>1?j+1:''}${p.rr&&p.rr[j]!=null?' · '+f2(p.rr[j])+'R':''}</small><b>${fp(t)}</b><i>${sg(Math.abs(t-p.vao))}</i></div>`).join('')
   +(p.tp.length>3?`<div class="tp"><small>Chốt lời xa nhất (mức ${p.tp.length})</small><b>${fp(p.tp[p.tp.length-1])}</b><i>còn ${p.tp.length-4} mức ở giữa, xem phân tích đầy đủ</i></div>`:'')
   +(mt?`<div class="mt"><small>Mục tiêu lý thuyết · ${f2(mt.r)}R</small><b>${fp(mt.gia)}</b><i title="${esc(mt.ten)}">${esc(mt.ten)}</i></div>`:'')+'</div>'
   +(bt?`<div class="btc" title="Đo trên vàng từ ${PTR.mo_hinh.tu_nam}, mỗi tín hiệu chấm riêng. Chốt càng gần thì thắng càng nhiều lần, nhưng mỗi lần thắng càng nhỏ."><span>Tỷ lệ thắng theo mức chốt:</span>`+bt.filter(r=>[.25,.5,1,2].includes(r[0])).map(r=>`<b class="${r[3]>0?'duong':''}">${soR(r[0])}R · ${String(r[2]).replace('.',',')}%</b>`).join('')+'</div>':'')
   +`<p class="why">${esc(p.ly_do||'')}${p.hieu_luc?'':' <b>Chỉ để tham khảo:</b> '+esc((p.vi_sao_het||[]).join(' '))}</p>`
   +(d&&d.ma==='lo'?'<p class="stale" style="margin:0"><b>Số đo quá khứ: lỗ ở cả hai nửa dữ liệu.</b></p>':'')
   +`<details class="plct"${plMo?' open':''}><summary>Số đo và giải thích</summary>`+soDo
   +(mt?`<p class="why">${tm&&tm.n?`Nếu chốt ở mục tiêu lý thuyết thay cho 2R: ${tm.n} lệnh, có lãi ${tm.ty_le.toFixed(1).replace('.',',')}%, ${(tm.usd_tb>0?'+':'−')+f2(Math.abs(tm.usd_tb))} USD mỗi lệnh.`:'Phần chạy lại trên dữ liệu chốt ở 2R.'}</p>`:'')
   +(kyLuat&&!kl?'<p class="why"><b>Kỷ luật: đứng ngoài.</b> Chế độ này chỉ nhận điểm vào khi cả chiều lệnh của phương pháp lẫn bối cảnh giống lúc này (cùng phiên, cùng biên độ) đều có lãi ở nửa học và nửa kiểm, mỗi nửa ít nhất 30 lệnh. Với luật trong sổ, chiều lệnh đó ở các năm trước quãng này cũng phải có lãi.</p>':kyLuat&&kl?'<p class="why"><b>Kỷ luật: đạt.</b> Điểm vào này qua được các vòng lọc theo số đo quá khứ. Đó chưa phải bằng chứng có lợi thế: một bối cảnh không có lợi thế vẫn có khoảng một phần tư khả năng qua vòng "có lãi cả hai nửa" chỉ nhờ may, và kiểm định trên cả tập luật chưa cho thấy luật nào có lãi có ý nghĩa thống kê. Kỷ luật chỉ loại bớt chỗ đã thấy rõ là kém.</p>':'')
   +(d&&d.ma==='lo'?'<p class="why">Số đo quá khứ của phương án này là lỗ ở cả hai nửa dữ liệu. Trang nêu các mức giá đúng theo quy tắc của phương pháp để bạn biết, không phải để khuyên vào lệnh.</p>':'')
   +(bt?`<p class="why"><b>Vì sao tỷ lệ thắng thấp.</b> Tỷ lệ thắng đi liền với mức chốt lời: chốt càng xa thì càng ít lần tới. Bảng dưới là chính phương pháp này, chiều ${len?'MUA':'BÁN'}, trên vàng từ ${PTR.mo_hinh.tu_nam} (${bt[0][1].toLocaleString('vi-VN')} tín hiệu):</p><div class="btb"><b>Chốt ở</b><b>Thắng</b><b>Cần để hòa vốn</b><b>Trung bình mỗi lệnh</b>`+bt.map(r=>`<span>${soR(r[0])}R</span><span>${String(r[2]).replace('.',',')}%</span><span>hơn ${f2(100/(1+r[0])).replace(/,?0+$/,'')}%</span><span class="${r[3]>0?'gain':'loss'}">${(r[3]>0?'+':'−')+f2(Math.abs(r[3]))}R</span>`).join('')+'</div><p class="why">Muốn thắng 85–90% số lệnh thì phải chốt ở khoảng 0,1–0,2R; khi đó một lệnh thua xóa nhiều lệnh thắng. Tỷ lệ thắng cao không đồng nghĩa với có lãi: cột cuối mới là thứ quyết định.</p>':'')
   +(p.dong_thuan&&PTR.mo_hinh&&PTR.mo_hinh.dong_thuan?(g=>`<p class="why"><b>Đồng thuận: ${p.dong_thuan.cung} phương pháp khác cùng chiều, ${p.dong_thuan.nguoc} ngược chiều trong ${g.phut/60} giờ qua.</b> Số đo trên vàng từ ${PTR.mo_hinh.tu_nam} (chốt 2R) (đếm trên mọi tín hiệu, như lúc chạy thật): không có phương pháp nào khác cùng chiều thì trung bình ${(g.cung[0][2]>0?'+':'−')+f2(Math.abs(g.cung[0][2]))}R mỗi lệnh, có một thì ${(g.cung[1][2]>0?'+':'−')+f2(Math.abs(g.cung[1][2]))}R, từ hai trở lên thì ${(g.cung[2][2]>0?'+':'−')+f2(Math.abs(g.cung[2][2]))}R. Khác biệt nhỏ và cả ba nhóm đều chưa có lãi, nên nhiều phương pháp cùng báo không phải lý do để tin điểm vào hơn.</p>`)(PTR.mo_hinh.dong_thuan):'')
   +(p.mo_hinh&&PTR.mo_hinh&&PTR.mo_hinh.san_sang?(m=>`<p class="why"><b>Điểm mô hình ${p.mo_hinh.hang}/100 (thử nghiệm).</b> Mô hình học từ ${m.n.toLocaleString('vi-VN')} tín hiệu trên vàng từ ${m.tu_nam} và xếp hạng điểm vào này so với chúng. Trên ${m.ngoai_mau.tu}–${m.ngoai_mau.den} là quãng mô hình chưa thấy, nhóm 10% điểm cao nhất thắng ${String(m.ngoai_mau.top10.ty_le).replace('.',',')}% ở 2R, trung bình ${(m.ngoai_mau.top10.r_tb>0?'+':'−')+f2(Math.abs(m.ngoai_mau.top10.r_tb))}R mỗi lệnh, so với ${(m.ngoai_mau.tat_ca.r_tb>0?'+':'−')+f2(Math.abs(m.ngoai_mau.tat_ca.r_tb))}R của mọi tín hiệu: ${m.ngoai_mau.top10.r_tb>0.05?'có lãi nhẹ khi chấm riêng từng tín hiệu, nhưng khi mô phỏng mỗi lúc một lệnh qua tám năm thì chỉ quanh hòa vốn và còn lỗ nhẹ; chưa được giá thật xác nhận':m.ngoai_mau.top10.r_tb>0?'tốt hơn mặt bằng nhưng mới quanh hòa vốn':'tốt hơn mặt bằng nhưng vẫn lỗ khi chấm riêng từng tín hiệu, nên chưa phải lợi thế'}.${m.ngoai_mau.bac?(t=>` Cùng nhóm đó khi chốt ở 1R: thắng ${String(t[2][2]).replace('.',',')}%, ${(t[2][3]>0?'+':'−')+f2(Math.abs(t[2][3]))}R mỗi lệnh.`)(m.ngoai_mau.bac.top10):''}${m.ngoai_mau.theo_nam?' Theo năm (chốt 2R): '+m.ngoai_mau.theo_nam.map(r=>r[0]+' '+(r[2]>0?'+':'−')+f2(Math.abs(r[2]))+'R').join(', ')+'.':''}${cvTxt(m)} Bật nút Mô hình ≥ 90 thì trang chỉ báo các điểm vào thuộc nhóm này. Đây là con số tham khảo, chưa phải tín hiệu.</p>`)(PTR.mo_hinh):'')
   +'<p class="why">Trang không đặt lệnh; đây không phải lời khuyên đầu tư.</p></details>'
   +phNgan(ppChon==='tat'?ptDs().filter(x=>x.nhom==='pp'&&bat(ppKhoa(x))):nh)
   +`<div class="pln"><button type="button" class="ictb dvv" aria-pressed="${ve}">${ve?'Đang vẽ trên biểu đồ':'Vẽ lên biểu đồ'}</button><button type="button" class="ictb dvm">Xem phân tích đầy đủ</button></div></div>`}
 else{const ten=tabs.find(t=>t[0]===ppChon)[1];
  h+=`<div class="pl"><p class="plk"><b>${ppChon==='tat'?'Chưa phương pháp nào có điểm vào lúc này.':'Chưa có điểm vào theo '+esc(ten)+'.'}</b> Trang không ép ra lệnh khi điều kiện chưa đủ.</p>`
   +(ppChon==='tat'?'':(o=>o.length?`<p class="why"><b>Phương pháp khác đang có điểm vào:</b> ${o.map(([k,n])=>`<button type="button" class="ictb ppj" data-k="${k}">${esc(n)}</button>`).join(' ')}</p>`:'')(tabs.filter(([k])=>k!=='tat'&&k!==ppChon&&tt(k))))
   +(ppChon==='tat'?'':nh.slice(0,4).map(x=>`<p class="why"><b>${esc(x.ten)}:</b> ${esc(x.vi_sao||'')}</p>`).join('')+(nh.some(x=>x.nhom==='pp')?`<details class="plct"${plMo?' open':''}><summary>Quy tắc của phương pháp</summary>${nh.filter(x=>x.nhom==='pp').slice(0,4).map(x=>`<p class="why"><b>${esc(x.ten)}:</b> ${esc(x.thong_ke||'')}</p>`).join('')}</details>`:''))
   +phNgan(ppChon==='tat'?ptDs().filter(x=>x.nhom==='pp'&&bat(ppKhoa(x))):nh)
   +'<div class="pln"><button type="button" class="ictb dvm">Xem phân tích đầy đủ</button></div></div>'}
 if(h===plH&&!el.hidden){plCach();return}plH=h;el.innerHTML=h;el.hidden=false;plCach();
 const kh=p?[p.ma,p.huong,p.vao,p.sl].join('|'):'';if(kh!==plKhoa){plKhoa=kh;const c=el.querySelector('.pl');if(c&&kh)c.classList.add('moi')}
 el.querySelectorAll('.ppx,.ppj').forEach(b=>b.addEventListener('click',()=>{ppChon=b.dataset.k;try{localStorage.setItem('so-ppc',ppChon)}catch(e){}planTat=0;plan=ppTot(ppChon);draw();dvVe();if(!PTB.hidden)ptVe()}));
 el.querySelectorAll('.dvv').forEach(b=>b.addEventListener('click',()=>{if(plan&&p&&plan.ma===p.ma){plan=null;planTat=1}else{plan=p;planTat=0}draw();dvVe();if(!PTB.hidden)ptVe()}));
 el.querySelectorAll('.vph').forEach(b=>b.addEventListener('click',()=>phBam(b.dataset.ma)));
 el.querySelectorAll('details.plct').forEach(dt=>dt.addEventListener('toggle',()=>{plMo=dt.open}));
 el.querySelectorAll('.kl').forEach(b=>b.addEventListener('click',()=>{kyLuat=!kyLuat;try{localStorage.setItem('so-kl',kyLuat?'1':'0')}catch(e){}plH='';dvVe()}));
 el.querySelectorAll('.mhl').forEach(b=>b.addEventListener('click',()=>{mhLoc=!mhLoc;try{localStorage.setItem('so-mh',mhLoc?'1':'0')}catch(e){}plH='';dvVe()}));
 el.querySelectorAll('.dvm').forEach(b=>b.addEventListener('click',()=>{if(PTB.hidden)ptVe();PTB.scrollIntoView({behavior:'smooth',block:'nearest'})}))}
function dvKiem(){if(!PTR)return;const now=Date.now(),sym=ma||'XAUUSD',pc=v=>v.toFixed(1).replace('.',',')+'%';
 DV=ptDs().filter(p=>p.co&&p.hieu_luc&&bat(ppKhoa(p))).map(p=>{const d=diem(p),st=d&&d.s,
   doo=st?`Từ ${new Date(hocMoc(p.ma.split(':')[0]).tu).getFullYear()}${PTR.khac_vang?' trên '+sym:''}, bối cảnh giống lúc này: ${st.n} lệnh, có lãi ${pc(st.ty_le)}, ${NX[d.ma][1].toLowerCase()}.`:HOC&&HOC.san_sang?'Chưa có số đo cho bối cảnh này.':'Đang đo trên dữ liệu của mã này.';
   return{p,do:doo,giu:klDat(p),k:[sym,p.ma,p.huong,p.vao,p.sl].join('|'),tieu:'Điểm vào còn hiệu lực: '+sym+' '+(p.huong==='MUA'?'MUA':'BÁN')+' '+fp(p.vao),nd:p.ten+'. Dừng lỗ '+fp(p.sl)+', chốt '+fp(p.tp[p.tp.length-1])+'. '+doo}});
 for(const a of DV){if(kyLuat&&!a.giu)continue;if(mhLoc&&PTR.mo_hinh&&PTR.mo_hinh.san_sang&&!(a.p.mo_hinh&&a.p.mo_hinh.hang>=90))continue;const cu=dvDa.get(a.k);if(cu&&now-cu<300000)continue;dvDa.set(a.k,now);toast({tieu_de:a.tieu,noi_dung:a.nd});if(snd)beep();
  if(window.Notification&&Notification.permission==='granted')try{new Notification(a.tieu,{body:a.nd,tag:'so-dv-'+a.k})}catch(e){}}
 try{sessionStorage.setItem('so-dv',JSON.stringify([...dvDa].slice(-60)))}catch(e){}dvVe()}
let ptDang=0,ptCho=0,ptLan=0;async function ptTai(tu){if(ptDang){if(!tu)ptCho=1;return}ptDang=1;ptLan=Date.now();const b=$('#pt-btn'),ma0=ma;if(!tu){planTat=0;b.disabled=true;b.setAttribute('aria-busy','true');b.textContent='Đang phân tích…'}
 try{const r=await fetch('/api/phan-tich'+(ma?'?ma='+encodeURIComponent(ma):''),{cache:'no-store'});if(!r.ok)throw new Error(await r.text());const j=await r.json();
  if(ma0===ma){PTR=j;
   if(!tu&&ppChon!=='tat'&&!ppNhom(ppChon).some(p=>p.co)&&ppNhom('tat').some(p=>p.co)){ppChon='tat';try{localStorage.setItem('so-ppc','tat')}catch(e){}}      // bấm nút mà thẻ đang nhớ không có điểm vào trong khi thẻ khác có: về 'Tất cả phương pháp'
   const ds=ptDs().filter(p=>bat(ppKhoa(p))),tn=totNhat();
   if(plan&&(plan.ma==='ai'||plan.nk)&&tu){}else if(plan&&plan.ph){const q=[...(PTR.phuong_phap||[]),...(PTR.phuong_an||[])].find(x=>x.phieu&&'phieu:'+x.phieu.ma===plan.ma);plan=q?phPlan(q.phieu):null}else{const cu=plan&&ppNhom(ppChon).find(p=>p.co&&p.ma===plan.ma);plan=cu||(tu&&planTat?null:ppTot(ppChon,tu&&ppChon==='tat'))}
   if(!tu){view.off=0;if(LW)lwNay()}if(!tu||!PTB.hidden)ptVe();draw();dvKiem();if(!KC||!KC.san_sang)kcTai();if(!HOC||!HOC.san_sang)hocTai();if(!tu&&hep()&&!fsOn())PTB.scrollIntoView({behavior:'smooth',block:'nearest'})}}
 catch(e){if(!tu){PTB.innerHTML='<p class="stale">'+(e instanceof TypeError?'Webapp không trả lời (có thể đang khởi động lại hoặc đã tắt). Chờ vài giây rồi bấm lại; nếu vẫn vậy, mở lại webapp.':'Không phân tích được: '+esc(e.message))+'</p>';PTB.hidden=false}}
 nkTai();ptDang=0;if(!tu){b.disabled=false;b.removeAttribute('aria-busy');b.textContent='Phân tích điểm vào'}if(ptCho){ptCho=0;ptTai(0)}}
$('#pt-btn').addEventListener('click',()=>{if(PTR&&PTB.hidden)ptVe();ptTai(0)});
// phân tích tự chạy từ lúc mở trang: 15 giây một lần khi có giá trực tiếp, một phút một lần khi không
setInterval(()=>{if(document.visibilityState!=='visible'||!D)return;const song=D.nguon==='mt5'&&!(D.luat&&D.luat.tuoi_phut>20);if(!PTR||Date.now()-ptLan>=(song?15000:60000)-500)ptTai(1)},5000);
// --- toàn màn hình (dùng API của trình duyệt; không được thì phóng to trong trang)
const FS=$('#fs-btn'),GOC=document.documentElement,fsOn=()=>CP.classList.contains('max');let fsLuc=0;
const fsDat=on=>{CP.classList.toggle('max',on);GOC.classList.toggle('khoa',on);FS.textContent=on?'Thu nhỏ':'Toàn màn hình';FS.setAttribute('aria-pressed',on);
 if(on)$('.stage').appendChild(PTB);else $('.col').prepend(PTB);setTimeout(fit,60)};
const GB=$('#gon-btn');let gon=1;try{gon=localStorage.getItem('so-gon-tren')==='0'?0:1}catch(e){}
const gonDat=v=>{gon=v?1:0;CP.classList.toggle('gon',!!gon);GB.innerHTML='<span class="gm" aria-hidden="true">'+(gon?'▼':'▲')+'</span><span class="gt">'+(gon?'Hiện phần trên':'Ẩn phần trên')+'</span>';
 const t=(gon?'Hiện lại thanh công cụ, dải tín hiệu bot và thẻ điểm vào':'Ẩn thanh công cụ phụ, dải tín hiệu bot và thẻ điểm vào để biểu đồ lớn nhất')+' (phím H)';GB.title=t;GB.setAttribute('aria-label',t);
 GB.setAttribute('aria-expanded',String(!gon));try{localStorage.setItem('so-gon-tren',gon?'1':'0')}catch(e){}if(fsOn())setTimeout(fit,60)};
gonDat(gon);GB.addEventListener('click',()=>gonDat(!gon));
if(window.ResizeObserver){let rq=0;new ResizeObserver(()=>{cancelAnimationFrame(rq);rq=requestAnimationFrame(fit)}).observe(C)}
FS.addEventListener('click',()=>{const on=!fsOn();fsDat(on);
 if(on){try{const q=GOC.requestFullscreen&&GOC.requestFullscreen();if(q&&q.catch)q.catch(()=>{})}catch(e){}}
 else if(document.fullscreenElement){const q=document.exitFullscreen();if(q&&q.catch)q.catch(()=>{})}});
if(ANH){fsDat(true);const b=document.createElement('div');b.className='anh-dau';b.textContent=document.title.split(' · ').slice(1).join(' · ');$('.stage').appendChild(b);(async()=>{const t0=Date.now();while(!D&&Date.now()-t0<15000)await new Promise(r=>setTimeout(r,200));if(D)nkTai();else document.documentElement.dataset.anh='loi'})()}
document.addEventListener('fullscreenchange',()=>{if(document.fullscreenElement){fsLuc=Date.now()}else{if(fsLuc&&Date.now()-fsLuc>500&&fsOn())fsDat(false);fsLuc=0}});
addEventListener('keydown',e=>{if(e.key==='Escape'&&fsOn()&&!document.fullscreenElement)fsDat(false)});
async function loop(){if(document.visibilityState==='visible')await load(1);setTimeout(loop,D&&D.nguon==='mt5'?(ES?15000:5000):60000)}
fit();cb();setInterval(cb,10000);cotTai();setInterval(cotTai,1800000);load().then(()=>{ai();setTimeout(loop,D&&D.nguon==='mt5'?5000:60000)});
setInterval(()=>{if(!$('#ask')||!$('#ask').textContent.startsWith('Đang'))ai()},60000)})();
"""


def trang_bieu_do(ten: str) -> str:
    chips = [('ema20', 'EMA20', 'var(--series)'), ('ema50', 'EMA50', 'var(--ema50)'), ('bb', 'Dải Bollinger', 'var(--mute)'),
             ('sr', 'Hỗ trợ / kháng cự', 'var(--ink2)'), ('fvg', 'Khoảng trống giá', 'var(--fvg)'), ('ob', 'Khối lệnh', 'var(--ob)'),
             ('tin', 'Giờ tin USD', 'var(--warn)'), ('lenh', 'Lệnh đang mở', 'var(--gain)'), ('bot', 'Lệnh của bot tín hiệu', 'var(--series)'),
             ('rsi', 'RSI14', 'var(--series)')]
    tfs = ''.join(f'<button type="button" data-tf="{t}" aria-pressed="{"true" if t == "M15" else "false"}">{t}</button>'
                  for t in ('M5', 'M15', 'M30', 'H1', 'H4', 'D1'))
    chip_html = ''.join(f'<button type="button" class="chip" data-k="{k}" aria-pressed="true" style="--c:{c}"><i></i>{escape(n)}</button>' for k, n, c in chips)
    extra = ':root{--ema50:#eb6834;--ob:#6250d6;--fvg:#eda100}:root[data-theme="dark"]{--ema50:#d95926;--ob:#9085e9;--fvg:#c98500}' \
            '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ema50:#d95926;--ob:#9085e9;--fvg:#c98500}}'
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.BIEU_TUONG}<title>Biểu đồ vàng · {escape(ten)}</title><style>{trang.CSS}{extra}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'bieu-do', '<button id="theme" type="button">Nền tối</button>') + '<main>',
        '<div class="top"><div><h1 id="tieu-de">Biểu đồ vàng</h1></div><div class="stamp"><span id="ma-nhan">XAUUSD · luật tính trên nến đã đóng</span><br><span id="src">đang tải…</span></div></div>',
        '<p class="note" id="doc-truoc"><b>Đọc trước:</b> các ô bên phải cho biết luật bạn đã viết đang nói gì trên nến đã đóng gần nhất. '
        'Theo chính báo cáo của bạn, chưa luật nào được chứng minh là có lãi. Trang này không đặt lệnh và không phải lời khuyên đầu tư.</p>',
        '<div class="desk"><div class="panel chartp" id="cp">',
        '<div class="tools"><label class="sel"><select id="ma" aria-label="Chọn mã" title="Các mã đang hiện trong Market Watch của MT5">'
        '<option value="">XAUUSDp · Gold vs US Dollar</option></select></label>'
        f'<div class="seg tf" role="group" aria-label="Khung thời gian">{tfs}</div>'
        '<div class="seg zo" role="group" aria-label="Phóng to, thu nhỏ">'
        '<button type="button" id="z-out" aria-label="Thu nhỏ" title="Thu nhỏ (phím −)"></button>'
        '<button type="button" id="z-in" aria-label="Phóng to" title="Phóng to (phím +)"></button>'
        '<button type="button" id="z-now" aria-label="Về hiện tại" title="Về hiện tại (phím 0)" disabled></button></div>'
        '<span class="grow"></span><button type="button" class="act" id="pt-btn" title="Phân tích điểm vào (phím A)">Phân tích điểm vào</button>'
        '<button type="button" class="ghost" id="gon-btn" aria-expanded="true"></button>'
        '<button type="button" class="ghost" id="fs-btn" aria-pressed="false" title="Toàn màn hình (phím F)">Toàn màn hình</button></div>',
        '<div class="tools t2"><div class="seg bo" role="group" aria-label="Bộ chỉ báo"><button type="button" data-bo="gon" title="EMA20, EMA50, hỗ trợ/kháng cự, lệnh đang mở">Gọn</button>'
        '<button type="button" data-bo="du" title="Bật mọi chỉ báo">Đầy đủ</button></div>'
        '<details class="tuy"><summary class="ghost nho" title="Bật tắt từng chỉ báo">Chỉ báo <b id="so-cb"></b></summary>'
        f'<div class="chips pop" role="group" aria-label="Chỉ báo">{chip_html}</div></details>'
        '<div class="seg kieu" role="group" aria-label="Kiểu biểu đồ"><button type="button" data-kieu="toi">Nền tối</button><button type="button" data-kieu="sang">Nền trắng</button>'
        '<button type="button" data-kieu="mt5">Nền đen MT5</button></div></div>',
        '<div class="bott" id="bot-tt" aria-live="polite"></div>',
        '<div class="stage" data-tai="1"><div id="lw"></div><canvas id="lwo" aria-hidden="true"></canvas><canvas id="cv" role="img" aria-label="Biểu đồ nến XAUUSD"></canvas><div id="read"></div></div>',
        '<div class="dvb" id="dv" aria-live="polite" hidden></div>',
        '<details class="plct hint"><summary>Cách dùng và phím tắt</summary><p class="why">Lăn chuột để phóng to, thu nhỏ. Kéo để xem lùi. Bấm đúp để về hiện tại. Nến mờ ở cuối là nến đang chạy. Phím tắt: 1–6 đổi khung, + và − phóng to thu nhỏ, ← → xem lùi và tiến, 0 về hiện tại, A phân tích, F toàn màn hình, H ẩn hoặc hiện phần phía trên khi toàn màn hình, Ctrl+Z hoàn tác hình vẽ, Delete xóa hình đang chọn, Esc thôi công cụ đang cầm.</p></details><p class="hint"><span id="his"></span> Biểu đồ vẽ bằng <a href="https://www.tradingview.com/" target="_blank" rel="noopener">TradingView Lightweight Charts™</a>. <span id="err"></span></p></div>',
        '<div class="col" data-tab="cb"><aside class="panel side tkt" id="tkt" aria-label="Tóm tắt tài khoản và rủi ro"><p class="why">Đang đọc tài khoản…</p></aside>'
        '<aside id="pt" class="pt panel side" hidden aria-label="Kết quả phân tích"></aside>'
        '<div class="ctab" role="tablist" aria-label="Thông tin bên phải"><button type="button" role="tab" data-t="cb">Cảnh báo<b id="cb-moi" hidden></b></button>'
        '<button type="button" role="tab" data-t="tk">Lệnh</button><button type="button" role="tab" data-t="nk">Nhật ký</button><button type="button" role="tab" data-t="rk">Tính lot</button></div>'
        '<aside class="panel side tabp" data-t="cb" id="cb" role="tabpanel"><h3>Cảnh báo</h3><p class="why">Đang tải…</p></aside><aside class="panel side tabp" data-t="tk" id="tk" role="tabpanel" aria-label="Tài khoản MT5"><h3>Tài khoản MT5</h3><p class="why">Đang đọc tài khoản…</p></aside><aside class="panel side tabp" data-t="nk" id="nk" role="tabpanel" aria-label="Nhật ký điểm vào"><h3>Nhật ký điểm vào</h3><p class="why">Đang đọc nhật ký…</p></aside>'
        '<aside class="panel side tabp" data-t="rk" id="rk" role="tabpanel"><h3>Tính khối lượng lệnh</h3>'
        '<label class="fld">Vốn (USD)<input id="rk-von" type="number" min="1" step="10" inputmode="decimal"></label>'
        '<label class="fld">Rủi ro mỗi lệnh (%)<input id="rk-rr" type="number" min="0.1" max="100" step="0.1" inputmode="decimal"></label>'
        '<label class="fld">Khoảng cách SL (giá)<input id="rk-sl" type="number" min="0.1" step="0.5" inputmode="decimal"></label>'
        '<button type="button" class="ghost nho" id="rk-atr">Lấy SL = 1,5 × ATR M15</button><div id="rko"></div>'
        '<p class="why">Tính theo 1 lot = 100 ounce, tức 0,01 lot lãi lỗ 1 USD cho mỗi 1 giá, như thông số hợp đồng trong tài liệu của bạn. '
        'Đây là phép tính, không phải lời khuyên đầu tư.</p></aside>'
        '<aside class="panel side" id="side"><p class="why">Đang tải…</p></aside>'
        '<aside class="panel side" id="cot" aria-label="Vị thế COT của vàng tương lai" hidden></aside>'
        '<aside class="panel side" id="ai"><h3>AI phân tích điểm vào</h3><p class="why">Đang tải…</p></aside></div></div>',
        '<footer><span id="chan-nguon">Giá đọc trực tiếp từ MT5 demo của bạn ở chế độ chỉ đọc; khi không nối được thì trang dùng kho nến 1 phút do hệ thống tự lưu. '
        'Trang không tự mở MT5 và không có lệnh đặt lệnh nào. Chỉ báo và luật gọi thẳng các hàm trong mã của bạn '
        '(bot tín hiệu, luật ba khung, luật đỉnh/đáy), tính trên nến đã đóng. </span>' + escape(trang.MIEN_TRU) + '</footer></main>',
        f'<script src="/tinh/lightweight-charts.js"></script><script>{trang.JS}</script><script>{JS}</script></body></html>'])
