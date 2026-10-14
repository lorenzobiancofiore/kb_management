#!/usr/bin/env python3
"""
Ontology viewer HTML (passo di presentazione, da kb_management/scripts/analysis/genera_ontology_viewer.py;
versione compatta, stesse sezioni: grafo entità, entità, relazioni B1/B2, timeline, aggiornamenti, avvisi).
Legge Knowledge Layer + Relazioni + Cronistoria (+ Catalogo) e produce un unico HTML offline.
La timeline è letta dalla prima chiave 'timeline_decisioni*' della Cronistoria (es. timeline_decisioni_cluster1).

Uso:
    python3 genera_ontology_viewer.py --knowledge-layer knowledge_layer_Water.json --relazioni relazioni_Water.json \
        --cronistoria cronistoria_Water.json --catalogo catalogo_Water.json --output ontology_viewer.html --titolo "..."
"""
import argparse
import html as html_lib
import json
from datetime import datetime, timezone
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if p and Path(p).exists() else None


TEMPLATE = r"""<!DOCTYPE html><html lang="it"><head><meta charset="utf-8"><title>__TITOLO__</title>
<style>
:root{--bg:#0f1115;--panel:#171a21;--panel2:#1e222b;--border:#2a2f3a;--text:#e6e8ec;--muted:#9aa3b2;--accent:#f59e0b}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--text)}
header{padding:14px 20px;border-bottom:1px solid var(--border);background:var(--panel);display:flex;gap:18px;flex-wrap:wrap;align-items:baseline}
header h1{font-size:17px;margin:0}.meta{font-size:12.5px;color:var(--muted)}.meta b{color:var(--text)}
nav{display:flex;gap:4px;padding:0 16px;background:var(--panel);border-bottom:1px solid var(--border);overflow-x:auto}
nav button{background:none;border:none;color:var(--muted);padding:10px 14px;font-size:13px;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
nav button.active{color:var(--text);border-bottom-color:var(--accent)}main{padding:16px 20px}.pane{display:none}.pane.active{display:block}
.gw{display:flex;gap:14px}.gc{width:250px;flex:0 0 250px;background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:13px}
.gc h3{font-size:12px;text-transform:uppercase;color:var(--muted);margin:14px 0 6px}.gc h3:first-child{margin-top:0}.gc label{display:flex;gap:6px;margin:4px 0}
input[type=text]{padding:6px 8px;border-radius:6px;border:1px solid var(--border);background:var(--panel2);color:var(--text);font-size:13px;width:100%}
.gc input[type=range]{width:100%}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
#host{flex:1;position:relative;background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden;height:620px}canvas{display:block;cursor:grab}
#side{position:absolute;top:10px;right:10px;width:290px;max-height:96%;overflow:auto;background:rgba(23,26,33,.97);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:12.5px;display:none}
#side .x{position:absolute;top:8px;right:10px;cursor:pointer;color:var(--muted)}.mz{border-top:1px solid var(--border);padding:6px 0}.mz .d{color:var(--accent);font-size:11.5px}.mz .c{color:var(--muted);font-size:11.5px}
table.dt{width:100%;border-collapse:collapse;font-size:13px}table.dt th{text-align:left;color:var(--muted);font-size:11.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);cursor:pointer}
table.dt td{padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}table.dt tr:hover td{background:var(--panel2)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#3f3f4655}
.persona{color:#93b4fb}.sistema_tool{color:#6ee7b7}.riferimento_normativo{color:#fbbf24}
.det{background:var(--panel);border:1px solid var(--border);border-radius:8px;margin-bottom:6px}.det>summary{padding:8px 12px;cursor:pointer;display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}.det .in{padding:4px 14px 12px}.det table.dt{margin:6px 0}.chip{display:inline-block;padding:2px 9px;margin:2px 4px 2px 0;border-radius:10px;border:1px solid var(--border);background:var(--panel2);color:var(--text);font-size:12px;cursor:pointer}.sub{color:var(--muted);font-size:12px}.kpi{border-top:1px solid var(--border);padding:6px 0}.card{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin-bottom:10px}.card h4{margin:0 0 6px;font-size:14px}
.empty{color:var(--muted);padding:20px 0}.code{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--muted)}.fr{margin-bottom:10px}
</style></head><body>
<header><h1>__TITOLO__</h1><span class="meta">generato il <b>__GEN__</b></span><span class="meta">__PER__</span>
<span class="meta"><b>__NE__</b> entità · <b>__NA__</b> co-menzioni · <b>__NB1__</b> ruoli dichiarati · <b>__NB2__</b> azioni con responsabile · <b>__NO__</b> oggetti dati · <b>__NR__</b> report · <b>__NL__</b> archi di lineage</span></header>
<nav><button class="tb active" data-t="grafo">Grafo entità</button><button class="tb" data-t="entita">Entità</button><button class="tb" data-t="ogg">Oggetti dati</button><button class="tb" data-t="rep">Report e KPI</button><button class="tb" data-t="lin">Lineage</button><button class="tb" data-t="ing">Ingestione</button><button class="tb" data-t="rel">Relazioni dichiarate</button><button class="tb" data-t="tl">Timeline decisioni</button><button class="tb" data-t="agg">Possibili aggiornamenti</button><button class="tb" data-t="av">Avvisi qualità dati</button></nav>
<main>
<section class="pane active" id="p-grafo"><div class="gw"><div class="gc">
<h3>Ricerca</h3><input type="text" id="search" placeholder="cerca un'entità...">
<h3>Tipo entità</h3>
<label><input type="checkbox" class="tcb" value="persona" checked><span class="dot" style="background:#2563eb"></span>Persone</label>
<label><input type="checkbox" class="tcb" value="sistema_tool" checked><span class="dot" style="background:#059669"></span>Sistemi/tool</label>
<label><input type="checkbox" class="tcb" value="riferimento_normativo" checked><span class="dot" style="background:#d97706"></span>Riferimenti normativi</label>
<h3>Peso minimo co-menzione</h3><input type="range" id="pm" min="1" max="30" value="8"><div class="meta" id="pml">≥ 8 documenti condivisi</div>
<h3>Isolati</h3><label><input type="checkbox" id="hi" checked>Nascondi entità senza archi visibili</label>
<h3>Info</h3><div class="meta">Trascina i nodi, rotella per zoom. Clic su un nodo per le menzioni. Il grafo mostra solo il Livello A (co-occorrenza documentale, nessuna relazione causale).</div></div>
<div id="host"><canvas id="cv"></canvas><div id="side"><span class="x" id="sx">✕</span><div id="sb"></div></div></div></div></section>
<section class="pane" id="p-entita"><div class="fr"><input type="text" id="es" placeholder="filtra per nome o alias..."></div><div style="max-height:640px;overflow:auto"><table class="dt" id="et"><thead><tr><th data-k="nome">Nome canonico</th><th data-k="tipo">Tipo</th><th data-k="alias">Alias</th><th data-k="n_menzioni">Menzioni</th><th data-k="ultima">Ultima menzione</th></tr></thead><tbody></tbody></table></div></section>
<section class="pane" id="p-ogg"><div class="fr"><input type="text" id="os" placeholder="cerca vista/tabella o campo (es. V_CASHIN_HEADER_YTV, IBAN, scadenza)..."></div><div class="meta" id="oc" style="margin-bottom:8px"></div><div id="ol"></div></section>
<section class="pane" id="p-rep"><div class="fr"><input type="text" id="rs" placeholder="cerca report o KPI (es. Unpaid Ratio, RQTI, aging)..."></div><div class="meta" id="rc" style="margin-bottom:8px"></div><div id="rl"></div></section>
<section class="pane" id="p-lin"><div class="fr"><input type="text" id="ls" placeholder="cerca un report o un oggetto dati per vederne il lineage..."></div><div id="lm" class="fr"></div><div id="ld"></div></section>
<section class="pane" id="p-ing"><div class="fr"><input type="text" id="is" placeholder="cerca un sistema (es. SAP, Salesforce, NET@2A)..."></div><div id="il"></div></section>
<section class="pane" id="p-rel"><h3 class="meta">LIVELLO B1 — ruolo dichiarato nel testo</h3><div style="max-height:250px;overflow:auto;margin-bottom:20px"><table class="dt" id="b1t"><thead><tr><th>Persona</th><th>Ruolo</th><th>Documento</th><th>Data</th></tr></thead><tbody></tbody></table></div>
<h3 class="meta">LIVELLO B2 — responsabile generico → azione</h3><div class="fr"><input type="text" id="b2s" placeholder="filtra..."></div><div style="max-height:360px;overflow:auto"><table class="dt" id="b2t"><thead><tr><th>Responsabile</th><th>Azione</th><th>Documento</th><th>Data</th><th>Scadenza</th></tr></thead><tbody></tbody></table></div></section>
<section class="pane" id="p-tl"><div id="tl"></div></section><section class="pane" id="p-agg"><div id="agg"></div></section><section class="pane" id="p-av"><div id="av"></div></section>
</main>
<script>
const D=__DATA__;
function esc(s){const d=document.createElement("div");d.textContent=(s==null?"":String(s));return d.innerHTML}
document.querySelectorAll(".tb").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tb").forEach(x=>x.classList.remove("active"));document.querySelectorAll(".pane").forEach(x=>x.classList.remove("active"));b.classList.add("active");document.getElementById("p-"+b.dataset.t).classList.add("active");if(b.dataset.t==="grafo")rs()});
let es={k:"n_menzioni",d:-1};
function rE(){const q=document.getElementById("es").value.trim().toLowerCase();let r=D.nodes.filter(n=>!q||n.nome.toLowerCase().includes(q)||(n.alias||[]).some(a=>a.toLowerCase().includes(q)));
r.sort((a,b)=>{let x=a[es.k],y=b[es.k];if(es.k==="ultima"){x=a.ultima_menzione?a.ultima_menzione.data||"":"";y=b.ultima_menzione?b.ultima_menzione.data||"":""}if(es.k==="alias"){x=(a.alias||[]).join();y=(b.alias||[]).join()}return typeof x==="string"?es.d*x.localeCompare(y):es.d*((x||0)-(y||0))});
document.querySelector("#et tbody").innerHTML=r.map(n=>`<tr><td>${esc(n.nome)}</td><td><span class="pill ${n.tipo}">${esc(n.tipo)}</span></td><td>${esc((n.alias||[]).join(", "))}</td><td>${n.n_menzioni}</td><td>${n.ultima_menzione?esc(n.ultima_menzione.data):"—"}</td></tr>`).join("")||`<tr><td colspan=5 class=empty>Nessun risultato.</td></tr>`}
document.getElementById("es").oninput=rE;document.querySelectorAll("#et th").forEach(th=>th.onclick=()=>{es.d=es.k===th.dataset.k?-es.d:-1;es.k=th.dataset.k;rE()});
function rB1(){document.querySelector("#b1t tbody").innerHTML=D.b1.map(r=>`<tr><td>${esc(r.persona)}</td><td>${esc(r.ruolo)}</td><td class=code>${esc(r.documento)}</td><td>${esc(r.data)}</td></tr>`).join("")||`<tr><td colspan=4 class=empty>Nessun arco B1: nei documenti Water le persone sono citate come partecipanti, non con ruoli dichiarati esplicitamente nel Knowledge Layer.</td></tr>`}
function rB2(){const q=document.getElementById("b2s").value.trim().toLowerCase();document.querySelector("#b2t tbody").innerHTML=D.b2.filter(r=>!q||(r.responsabile+r.azione).toLowerCase().includes(q)).map(r=>`<tr><td>${esc(r.responsabile)}</td><td>${esc(r.azione)}</td><td class=code>${esc(r.documento)}</td><td>${esc(r.data)}</td><td>${esc(r.scadenza)}</td></tr>`).join("")||`<tr><td colspan=5 class=empty>Nessun risultato.</td></tr>`}
document.getElementById("b2s").oninput=rB2;
document.getElementById("tl").innerHTML=D.timeline.map(t=>`<div class="card"><h4>${esc(t.data)} <span class=code>— ${esc(t.documento)}</span></h4><div class=meta>fonte data: ${esc(t.fonte_data)}</div><ul>${(t.decisioni||[]).map(d=>`<li>${esc(d)}</li>`).join("")}</ul></div>`).join("")||'<div class=empty>Nessuna voce.</div>';
document.getElementById("agg").innerHTML=D.agg.map(a=>{let st="";const stp=(x)=>x?`<div class="meta" style="margin:4px 0 0 10px"><b>${esc(x.data)}</b> <span class=code>(${esc(x.documento)})</span>: ${esc(x.testo)}</div>`:"";st+=stp(a.decisione_precedente)+stp(a.decisione_successiva)+stp(a.eseguita_in);if(a.evoluzione)st+=a.evoluzione.map(e=>`<div class="meta" style="margin:4px 0 0 10px"><b>${esc(e.data)}</b> <span class=code>(${esc(e.documento)})</span>: ${esc(e.stato)}</div>`).join("");return `<div class="card"><h4>${esc(a.tema)} <span class=pill>${esc(a.confidenza||"")}</span></h4>${st}${a.nota?`<div class=meta style="margin-top:6px">${esc(a.nota)}</div>`:""}</div>`}).join("")||'<div class=empty>Nessuna voce curata: il livello "possibili aggiornamenti" va compilato a mano a partire dalla timeline.</div>';
document.getElementById("av").innerHTML=D.av.map(a=>`<div class="card"><h4><span class=pill>${esc(a.tipo||"")}</span></h4><div style="margin:4px 0 6px">${esc(a.descrizione)}</div><div class=meta>${(a.documenti_coinvolti||a.documenti||[]).slice(0,12).map(d=>`<span class=code>${esc(d)}</span>`).join(" · ")}${(a.documenti_coinvolti||a.documenti||[]).length>12?" · …":""}</div></div>`).join("")||'<div class=empty>Nessun avviso.</div>';
rE();rB1();rB2();
function dets(sum,body){var d=document.createElement("details");d.className="det";var s=document.createElement("summary");s.innerHTML=sum;d.appendChild(s);var b=document.createElement("div");b.className="in";b.innerHTML=body;d.appendChild(b);return d}
function nq(s){return String(s||"").toLowerCase()}
function rO(){var q=nq(document.getElementById("os").value.trim()),L=D.ogg,res=L;
 if(q){var qt=q.split(/\s+/);res=L.filter(function(o){var n=nq(o.nome+" "+(o.alias||[]).join(" ")+" "+(o.sistema||""));return qt.every(function(t){return n.indexOf(t)>-1})||o.campi.some(function(c){var cn=nq(c.n);return qt.every(function(t){return cn.indexOf(t)>-1})})})}
 var host=document.getElementById("ol");host.innerHTML="";document.getElementById("oc").textContent=res.length+" oggetti"+(res.length>150?" (primi 150: restringi la ricerca)":"");
 res.slice(0,150).forEach(function(o){var qt=q?q.split(/\s+/):[];var camp=o.campi;var hit=0;if(qt.length){camp=o.campi.filter(function(c){var cn=nq(c.n);return qt.every(function(t){return cn.indexOf(t)>-1})});hit=camp.length;if(!hit)camp=o.campi}
  var body=(o.descrizione?"<p>"+esc(o.descrizione)+"</p>":"")+(o.logica?"<p class=meta><b>Logica/filtri:</b> "+esc(o.logica)+"</p>":"")
   +"<table class=dt><thead><tr><th>Campo</th><th>Tipo</th><th>Chiave</th><th>Descrizione</th><th>Origine</th></tr></thead><tbody>"+camp.slice(0,120).map(function(c){return "<tr><td><b>"+esc(c.n)+"</b></td><td>"+esc(c.t)+"</td><td>"+(c.k?"sì":"")+"</td><td>"+esc(c.d)+(c.alt?" <span class=sub>("+c.alt+" descrizioni alternative)</span>":"")+"</td><td>"+esc(c.o)+"</td></tr>"}).join("")+"</tbody></table>"
   +(o.campi.length>120&&!hit?"<div class=meta>Mostrati 120 campi su "+o.campi.length+"</div>":"")
   +(o.rel.length?"<p class=meta><b>Relazioni:</b> "+o.rel.map(function(r){return esc(r.tipo)+" "+esc(r.con)+(r.cond?" ("+esc(r.cond)+")":"")}).join("; ")+"</p>":"")
   +"<p class=meta><b>Documenti:</b> "+o.docs.map(function(d){return "<span class=code>"+esc(d)+"</span>"}).join(" · ")+"</p>"
   +(o.avvisi.length?"<p class=meta><b>Avvisi:</b> "+o.avvisi.map(esc).join(" · ")+"</p>":"");
  host.appendChild(dets("<b>"+esc(o.nome)+"</b><span class=pill>"+esc(o.tipo||"oggetto")+"</span><span class=sub>"+esc(o.sistema||"sistema n.d.")+" · "+o.campi.length+" campi"+(hit?" · "+hit+" corrispondono":"")+"</span>",body))});}
function rR(){var q=nq(document.getElementById("rs").value.trim()),qt=q?q.split(/\s+/):[],res=D.rep.filter(function(r){if(!qt.length)return true;var n=nq(r.nome+" "+(r.alias||[]).join(" "));return qt.every(function(t){return n.indexOf(t)>-1})||r.v.some(function(v){return v.kpi.some(function(k){var kn=nq(k.n);return qt.every(function(t){return kn.indexOf(t)>-1})})})});
 var host=document.getElementById("rl");host.innerHTML="";document.getElementById("rc").textContent=res.length+" report"+(res.length>100?" (primi 100)":"");
 res.slice(0,100).forEach(function(r){var body=(r.scopo?"<p>"+esc(r.scopo)+"</p>":"")+r.v.map(function(v){return "<div class=kpi><div><span class=code>"+esc(v.doc)+"</span> <span class=sub>"+esc(v.data||"")+(v.stato?" · "+esc(v.stato):"")+"</span></div>"
   +(v.fonti.length?"<div class=meta><b>Fonti dati:</b> "+v.fonti.map(esc).join(", ")+"</div>":"")+(v.filtri.length?"<div class=meta><b>Filtri visuali:</b> "+v.filtri.map(esc).join(", ")+"</div>":"")
   +v.kpi.map(function(k){return "<div style='margin:6px 0 0 8px'><b>"+esc(k.n)+"</b>"+(k.norm?" <span class=sub>"+esc(k.norm)+"</span>":"")+"<div>"+(k.l?esc(k.l):"<span class=sub>logica di calcolo non dichiarata nel documento</span>")+"</div>"+(k.f.length?"<div class=sub>Filtri: "+k.f.map(esc).join(", ")+"</div>":"")+(k.src.length?"<div class=sub>Fonti: "+k.src.map(esc).join(", ")+"</div>":"")+"</div>"}).join("")+"</div>"}).join("");
  host.appendChild(dets("<b>"+esc(r.nome)+"</b><span class=sub>"+r.nk+" KPI · "+r.v.length+" document"+(r.v.length==1?"o":"i")+"</span>",body))});}
var LIN_UP={},LIN_DOWN={},LIN_ENT={};
(function(){D.lin.forEach(function(e){(LIN_UP[e.da.id]=LIN_UP[e.da.id]||[]).push(e);if(e.a.id)(LIN_DOWN[e.a.id]=LIN_DOWN[e.a.id]||[]).push(e);LIN_ENT[e.da.id]=e.da;if(e.a.id)LIN_ENT[e.a.id]=e.a});D.ogg.forEach(function(o){LIN_ENT[o.id]={id:o.id,n:o.nome,tp:"oggetto_dati"}});D.rep.forEach(function(r){LIN_ENT[r.id]={id:r.id,n:r.nome,tp:"report"}})})();
function lShow(id){var e=LIN_ENT[id]||{n:id,tp:""},up=LIN_UP[id]||[],dn=LIN_DOWN[id]||[],host=document.getElementById("ld");
 function row(x,peer,dir){var ent=dir=="up"?x.a:x.da;var nm=ent.n||ent.v||"";var link=ent.id&&LIN_ENT[ent.id]?"<a href='#' data-id='"+esc(ent.id)+"' class=lk>"+esc(nm)+"</a>":esc(nm)+(ent.r===false?" <span class=sub>(non riconosciuto)</span>":"");return "<tr><td>"+esc(x.t)+"</td><td>"+link+"</td><td><span class=pill>"+esc(ent.tp||"")+"</span></td><td class=code>"+esc(x.d)+"</td></tr>"}
 function tbl(list,dir){return list.length?"<table class=dt><thead><tr><th>Relazione</th><th>"+(dir=="up"?"Verso":"Da")+"</th><th>Tipo</th><th>Documento</th></tr></thead><tbody>"+list.slice(0,200).map(function(x){return row(x,null,dir)}).join("")+"</tbody></table>"+(list.length>200?"<div class=meta>primi 200 su "+list.length+"</div>":""):"<div class=empty>Nessun arco dichiarato.</div>"}
 host.innerHTML="<div class=card><h4>"+esc(e.n)+" <span class=pill>"+esc(e.tp||"")+"</span></h4><div class=meta>Archi dichiarati nei documenti, senza inferenze.</div></div><h4>Dipende da / usa ("+up.length+")</h4>"+tbl(up,"up")+"<h4>Usato da ("+dn.length+")</h4>"+tbl(dn,"dn");
 [].forEach.call(host.querySelectorAll("a.lk"),function(a){a.onclick=function(ev){ev.preventDefault();lShow(a.getAttribute("data-id"));window.scrollTo(0,0)}})}
function rL(){var q=nq(document.getElementById("ls").value.trim()),m=document.getElementById("lm");m.innerHTML="";if(!q)return;var qt=q.split(/\s+/);var c=Object.keys(LIN_ENT).filter(function(id){var e=LIN_ENT[id];return (e.tp=="report"||e.tp=="oggetto_dati")&&qt.every(function(t){return nq(e.n).indexOf(t)>-1})}).slice(0,24);
 c.forEach(function(id){var b=document.createElement("span");b.className="chip";b.textContent=LIN_ENT[id].n+" ("+LIN_ENT[id].tp+")";b.onclick=function(){lShow(id)};m.appendChild(b)});if(!c.length)m.innerHTML="<span class=empty>Nessun report o oggetto trovato.</span>"}
function rI(){var q=nq(document.getElementById("is").value.trim()),qt=q?q.split(/\s+/):[],host=document.getElementById("il");host.innerHTML="";
 D.ing.filter(function(g){return !qt.length||qt.every(function(t){return nq(g.nome+" "+(g.alias||[]).join(" ")).indexOf(t)>-1})}).slice(0,120).forEach(function(g){var body=g.v.slice(0,12).map(function(v){return "<div class=kpi><span class=code>"+esc(v.doc)+"</span> <span class=sub>"+esc(v.data||"")+"</span><div><b>Stato:</b> "+esc(v.stato||"n.d.")+" · <b>Modalità:</b> "+esc(v.mod||"n.d.")+" · <b>Frequenza:</b> "+esc(v.freq||"n.d.")+"</div>"+(v.note?"<div class=meta>"+esc(v.note)+"</div>":"")+(v.ogg.length?"<div class=meta><b>Oggetti ("+v.ogg.length+"):</b> "+v.ogg.slice(0,40).map(esc).join(", ")+(v.ogg.length>40?" …":"")+"</div>":"")+"</div>"}).join("")+(g.v.length>12?"<div class=meta>primi 12 documenti su "+g.v.length+"</div>":"");
  var last=g.v[0]||{};host.appendChild(dets("<b>"+esc(g.nome)+"</b><span class=sub>stato più recente: "+esc(last.stato||"n.d.")+" · "+g.v.length+" document"+(g.v.length==1?"o":"i")+"</span>",body))})}
["os","rs","ls","is"].forEach(function(id,i){document.getElementById(id).oninput=[rO,rR,rL,rI][i]});
[["ogg",D.ogg],["rep",D.rep],["lin",D.lin],["ing",D.ing]].forEach(function(x){if(!x[1].length)[].forEach.call(document.querySelectorAll(".tb"),function(b){if(b.dataset.t===x[0])b.style.display="none"})});
rO();rR();rI();

const cv=document.getElementById("cv"),cx=cv.getContext("2d"),side=document.getElementById("side"),sb=document.getElementById("sb");document.getElementById("sx").onclick=()=>side.style.display="none";
const COL={persona:"#2563eb",sistema_tool:"#059669",riferimento_normativo:"#d97706"};const nb={};D.nodes.forEach(n=>nb[n.id]=n);
const sn=D.nodes.map(n=>({id:n.id,tipo:n.tipo,nome:n.nome,n_menzioni:n.n_menzioni,x:(Math.random()-.5)*500,y:(Math.random()-.5)*500,vx:0,vy:0,fixed:false}));const snb={};sn.forEach(n=>snb[n.id]=n);
let vn=[],ve=[],sel=null,hov=null,camX=0,camY=0,zoom=1;
function af(){const on=new Set([...document.querySelectorAll(".tcb:checked")].map(c=>c.value));const pm=+document.getElementById("pm").value,hi=document.getElementById("hi").checked,q=document.getElementById("search").value.trim().toLowerCase();
ve=D.edges_a.filter(e=>e.peso>=pm&&nb[e.source]&&nb[e.target]&&on.has(nb[e.source].tipo)&&on.has(nb[e.target].tipo));const c=new Set();ve.forEach(e=>{c.add(e.source);c.add(e.target)});
vn=sn.filter(n=>on.has(n.tipo)&&(!hi||c.has(n.id)));vn.forEach(n=>n._m=q&&n.nome.toLowerCase().includes(q))}
document.querySelectorAll(".tcb").forEach(c=>c.onchange=af);document.getElementById("hi").onchange=af;document.getElementById("search").oninput=af;
document.getElementById("pm").oninput=()=>{document.getElementById("pml").textContent="≥ "+document.getElementById("pm").value+" documenti condivisi";af()};
function rs(){const h=document.getElementById("host");cv.width=h.clientWidth;cv.height=h.clientHeight}window.onresize=rs;
function step(){const n=vn.length;for(let i=0;i<n;i++){const a=vn[i];if(a.fixed)continue;let fx=0,fy=0;for(let j=0;j<n;j++){if(i===j)continue;const b=vn[j];const dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01,d=Math.sqrt(d2),r=1800/d2;fx+=dx/d*r;fy+=dy/d*r}fx-=a.x*.006;fy-=a.y*.006;a.vx=(a.vx+fx*.02)*.82;a.vy=(a.vy+fy*.02)*.82}
ve.forEach(e=>{const a=snb[e.source],b=snb[e.target];if(!a||!b)return;const dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1,t=70+30/Math.min(e.peso,6),f=(d-t)*.02,ux=dx/d,uy=dy/d;if(!a.fixed){a.vx+=ux*f;a.vy+=uy*f}if(!b.fixed){b.vx-=ux*f;b.vy-=uy*f}});vn.forEach(a=>{if(!a.fixed){a.x+=a.vx;a.y+=a.vy}})}
function draw(){const W=cv.width,H=cv.height;cx.clearRect(0,0,W,H);cx.save();cx.translate(W/2+camX,H/2+camY);cx.scale(zoom,zoom);ve.forEach(e=>{const a=snb[e.source],b=snb[e.target];if(!a||!b)return;cx.strokeStyle=`rgba(148,163,184,${Math.min(.08+e.peso*.03,.6)})`;cx.beginPath();cx.moveTo(a.x,a.y);cx.lineTo(b.x,b.y);cx.stroke()});
const q=document.getElementById("search").value.trim();vn.forEach(n=>{const r=4+Math.min(Math.sqrt(n.n_menzioni)*1.6,12),s=n.id===sel,h=n.id===hov;cx.beginPath();cx.arc(n.x,n.y,s?r+3:r,0,6.2832);cx.fillStyle=COL[n.tipo]||"#888";cx.globalAlpha=(q&&!n._m)?.25:1;cx.fill();if(s||h){cx.lineWidth=2;cx.strokeStyle="#f59e0b";cx.stroke()}if(n._m||s||h){cx.globalAlpha=1;cx.fillStyle="#e6e8ec";cx.font="12px sans-serif";cx.fillText(n.nome,n.x+r+4,n.y+4)}cx.globalAlpha=1});cx.restore()}
function loop(){step();draw();requestAnimationFrame(loop)}
function wp(x,y){const r=cv.getBoundingClientRect();return{x:(x-r.left-cv.width/2-camX)/zoom,y:(y-r.top-cv.height/2-camY)/zoom}}
function na(x,y){const p=wp(x,y);let best=null,bd=16;vn.forEach(n=>{const d=Math.hypot(n.x-p.x,n.y-p.y);if(d<bd){bd=d;best=n}});return best}
let dn=null,pan=false,ps=null,moved=false;
cv.onmousedown=e=>{moved=false;const n=na(e.clientX,e.clientY);if(n){dn=n;n.fixed=true}else{pan=true;ps={x:e.clientX-camX,y:e.clientY-camY}}};
cv.onmousemove=e=>{if(dn){const p=wp(e.clientX,e.clientY);dn.x=p.x;dn.y=p.y;moved=true}else if(pan){camX=e.clientX-ps.x;camY=e.clientY-ps.y;moved=true}else{const n=na(e.clientX,e.clientY);hov=n?n.id:null;cv.style.cursor=n?"pointer":"grab"}};
window.onmouseup=()=>{if(dn)dn.fixed=false;dn=null;pan=false};
cv.onclick=e=>{if(moved)return;const n=na(e.clientX,e.clientY);if(n)op(n.id)};
cv.onwheel=e=>{e.preventDefault();zoom=Math.min(Math.max(zoom*(e.deltaY<0?1.08:.92),.2),4)};
function op(id){sel=id;const en=nb[id];const rel=D.edges_a.filter(e=>e.source===id||e.target===id).sort((a,b)=>b.peso-a.peso).slice(0,12).map(e=>{const o=nb[e.source===id?e.target:e.source];return`<div class=mz><b>${esc(o?o.nome:"")}</b> — peso ${e.peso}</div>`}).join("");
sb.innerHTML=`<h4>${esc(en.nome)}</h4><span class="pill ${en.tipo}">${esc(en.tipo)}</span>${(en.alias||[]).length?`<div class=meta>alias: ${esc(en.alias.join(", "))}</div>`:""}<h4 style="margin-top:12px">Menzioni (${en.menzioni.length})</h4>${en.menzioni.slice(0,15).map(m=>`<div class=mz><div class=d>${esc(m.documento)}</div><div class=meta>${esc(m.data)} · ${esc(m.tipo_documento)}</div><div class=c>${esc(m.contesto)}</div></div>`).join("")}${rel?`<h4 style="margin-top:12px">Co-menzionato con</h4>${rel}`:""}`;side.style.display="block"}
af();rs();requestAnimationFrame(loop);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--knowledge-layer", required=True)
    ap.add_argument("--relazioni", required=True)
    ap.add_argument("--cronistoria", required=True)
    ap.add_argument("--catalogo")
    ap.add_argument("--output", required=True)
    ap.add_argument("--titolo", default="Knowledge Base ETL Documentale")
    a = ap.parse_args()
    kl, rel, cr, cat = load(a.knowledge_layer) or {}, load(a.relazioni) or {}, load(a.cronistoria) or {}, load(a.catalogo)

    nodes = [{"id": e["id"], "tipo": e["tipo"], "nome": e["nome_canonico"], "alias": e.get("alias", []),
              "n_menzioni": len(e.get("menzioni", [])), "ultima_menzione": e.get("ultima_menzione"),
              "menzioni": e.get("menzioni", [])[:25]}
             for lista in ("persone", "sistemi_tool", "riferimenti_normativi") for e in kl.get(lista, [])]
    edges = [{"source": x["da"]["id"], "target": x["a"]["id"], "peso": x["peso"]}
             for x in rel.get("livello_a_co_menzione", [])]
    b1 = [{"persona": x["da"]["nome_canonico"], "ruolo": x["a"]["valore"], "documento": x.get("documento"), "data": x.get("data")}
          for x in rel.get("livello_b1_ruolo_dichiarato", [])]
    b2 = [{"responsabile": x["da"]["valore"], "azione": x["a"]["valore"], "documento": x.get("documento"),
           "data": x.get("data"), "scadenza": x.get("scadenza")} for x in rel.get("livello_b2_responsabile_azione", [])]

    def cl(x, n):
        x = "" if x is None else str(x)
        return x if len(x) <= n else x[: n - 1] + "…"

    ogg = [{"id": e["id"], "nome": e["nome_canonico"], "alias": e.get("alias", [])[:6], "tipo": e.get("tipo_oggetto"),
            "sistema": e.get("sistema_origine"), "descrizione": cl(e.get("descrizione"), 300), "logica": cl(e.get("logica_filtri"), 400),
            "campi": [{"n": c["nome"], "t": c.get("tipo"), "k": bool(c.get("chiave")), "d": cl(c.get("descrizione"), 140),
                       "o": cl(c.get("origine"), 80), "alt": len(c.get("descrizioni_alternative", [])) or None} for c in e.get("campi", [])],
            "rel": [{"tipo": r.get("tipo"), "con": r.get("con"), "cond": cl(r.get("condizione"), 120)} for r in e.get("relazioni", [])[:10]],
            "docs": [m["documento"] for m in e.get("menzioni", [])[:6]],
            "avvisi": [cl(a.get("avviso"), 140) for a in e.get("avvisi", [])[:3]]} for e in kl.get("oggetti_dati", [])]
    rep = [{"id": e["id"], "nome": e["nome_canonico"], "alias": e.get("alias", [])[:6], "scopo": cl(e.get("scopo"), 250), "nk": e.get("n_kpi", 0),
            "v": [{"doc": v["documento"], "data": v.get("data"), "stato": v.get("stato"), "fonti": (v.get("fonti_dati") or [])[:12],
                   "filtri": (v.get("filtri_visuali") or [])[:8],
                   "kpi": [{"n": k.get("nome"), "l": cl(k.get("logica_calcolo"), 500), "f": (k.get("filtri") or [])[:6],
                            "src": (k.get("fonti") or [])[:6], "norm": k.get("riferimento_normativo") or None} for k in (v.get("kpi") or [])[:25]]}
                  for v in e.get("versioni", [])[:4]]} for e in kl.get("report", [])]
    def nd(n):
        return {"id": n.get("id"), "n": n.get("nome_canonico") or n.get("valore"), "tp": n.get("tipo"), "r": n.get("risolto")}
    lin = [{"t": a["tipo_relazione"], "da": nd(a["da"]), "a": nd(a["a"]), "d": a.get("documento")} for a in rel.get("livello_b_lineage", [])]
    ing = [{"nome": e["nome_canonico"], "alias": e.get("alias", [])[:4],
            "v": [{"doc": v["documento"], "data": v.get("data"), "stato": v.get("stato"), "mod": v.get("modalita"), "freq": v.get("frequenza"),
                   "note": cl(v.get("note"), 200), "ogg": (v.get("oggetti") or [])} for v in e.get("versioni", [])]} for e in kl.get("ingestione_sistema", [])]

    tkey = next((k for k in cr if k.startswith("timeline_decisioni")), None)
    data = {"nodes": nodes, "edges_a": edges, "b1": b1, "b2": b2, "timeline": cr.get(tkey, []) if tkey else [],
            "agg": cr.get("possibili_aggiornamenti_decisioni", []), "av": cr.get("avvisi_qualita_dati", []),
            "ogg": ogg, "rep": rep, "lin": lin, "ing": ing}
    per = f"{cat['meta']['n_documents']} documenti · {cat['meta']['n_clusters']} cluster nel catalogo" if cat else ""
    out = (TEMPLATE.replace("__TITOLO__", html_lib.escape(a.titolo))
           .replace("__GEN__", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
           .replace("__PER__", html_lib.escape(per)).replace("__NE__", str(len(nodes)))
           .replace("__NA__", str(len(edges))).replace("__NB1__", str(len(b1))).replace("__NB2__", str(len(b2))).replace("__NO__", str(len(ogg))).replace("__NR__", str(len(rep))).replace("__NL__", str(len(lin)))
           .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")))
    Path(a.output).write_text(out, encoding="utf-8")
    print(f"Scritto: {a.output} | entità {len(nodes)} | archi A {len(edges)} | B2 {len(b2)}")


if __name__ == "__main__":
    main()
