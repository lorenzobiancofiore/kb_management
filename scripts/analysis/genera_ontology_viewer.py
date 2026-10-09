#!/usr/bin/env python3
"""
Generatore del visualizzatore HTML "ontology viewer" per una knowledge base
ETL documentale (Fase 4 Knowledge Layer + passo derivato Relazioni + Fase 5
Cronistoria).
=============================================================================
Non è una fase della pipeline a 5 fasi né il passo Relazioni: è un passo di
presentazione, a valle di tutto il resto, pensato per essere rilanciato ogni
volta che Knowledge Layer / Relazioni / Cronistoria vengono aggiornati (es.
dalla skill "etl-kb-build" dopo un'estensione). Produce un unico file HTML
autonomo (nessuna dipendenza esterna, nessuna chiamata di rete: apribile
anche offline via doppio click) con:

- un grafo interattivo delle entità canoniche (persone, sistemi_tool,
  riferimenti_normativi) e degli archi di co-menzione (Livello A di
  relazioni.py), con filtri per tipo entità, peso minimo dell'arco e
  ricerca testuale;
- una tabella delle entità con conteggio menzioni e ultima menzione;
- le relazioni dichiarate esplicitamente nel testo (Livello B1
  "ruolo_dichiarato" e B2 "responsabile_azione" di relazioni.py), che
  restano testo libero e quindi non entrano nel grafo delle entità
  canoniche (stessa scelta di design di relazioni.py: non creare
  un'entità canonica "ruolo/dominio");
- la timeline delle decisioni, i possibili aggiornamenti/sostituzioni tra
  decisioni e gli avvisi qualità dati dalla Cronistoria.

Uso:
    python3 genera_ontology_viewer.py \
        --knowledge-layer knowledge_layer_pilota.json \
        --relazioni relazioni_pilota.json \
        --cronistoria cronistoria_pilota.json \
        --catalogo catalogo_ProgettoDG.json \
        --output ontology_viewer.html \
        --titolo "Governance — Knowledge Base ETL Documentale"

--catalogo è opzionale (serve solo per mostrare qualche numero di perimetro
in testa alla pagina, tipo "N documenti coperti"); tutto il resto è
obbligatorio.

Generico e riutilizzabile su qualunque progetto che segua lo stesso schema
di output della pipeline (stessi nomi di campo, non stessi nomi di file):
non ha nulla hardcoded specifico di un progetto.
"""

import argparse
import html as html_lib
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def build_nodes_and_edges(kl):
    """Nodi = entità canoniche del Knowledge Layer. Ritorna (nodes, entita_by_id)."""
    nodes = []
    for tipo_lista in ("persone", "sistemi_tool", "riferimenti_normativi"):
        for ent in kl.get(tipo_lista, []) or []:
            nodes.append({
                "id": ent["id"],
                "tipo": ent["tipo"],
                "nome": ent["nome_canonico"],
                "alias": ent.get("alias", []) or [],
                "n_menzioni": len(ent.get("menzioni", []) or []),
                "ultima_menzione": ent.get("ultima_menzione"),
                "menzioni": ent.get("menzioni", []) or [],
            })
    return nodes


def build_edges_a(relazioni):
    edges = []
    for arco in relazioni.get("livello_a_co_menzione", []) or []:
        edges.append({
            "source": arco["da"]["id"],
            "target": arco["a"]["id"],
            "peso": arco["peso"],
            "documenti": [d.get("documento") for d in arco.get("documenti", [])][:6],
        })
    return edges


def build_b1(relazioni):
    out = []
    for arco in relazioni.get("livello_b1_ruolo_dichiarato", []) or []:
        out.append({
            "persona": arco["da"]["nome_canonico"],
            "persona_id": arco["da"]["id"],
            "ruolo": arco["a"]["valore"],
            "documento": arco.get("documento"),
            "data": arco.get("data"),
        })
    return out


def build_b2(relazioni):
    out = []
    for arco in relazioni.get("livello_b2_responsabile_azione", []) or []:
        out.append({
            "responsabile": arco["da"]["valore"],
            "azione": arco["a"]["valore"],
            "documento": arco.get("documento"),
            "data": arco.get("data"),
            "scadenza": arco.get("scadenza"),
        })
    return out


def build_meta(kl, relazioni, cronistoria, catalogo, titolo):
    n_persone = len(kl.get("persone", []) or [])
    n_sistemi = len(kl.get("sistemi_tool", []) or [])
    n_normative = len(kl.get("riferimenti_normativi", []) or [])
    meta = {
        "titolo": titolo,
        "generato_il": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "n_persone": n_persone,
        "n_sistemi_tool": n_sistemi,
        "n_riferimenti_normativi": n_normative,
        "n_entita_totali": n_persone + n_sistemi + n_normative,
        "n_archi_a": len(relazioni.get("livello_a_co_menzione", []) or []),
        "n_archi_b1": len(relazioni.get("livello_b1_ruolo_dichiarato", []) or []),
        "n_archi_b2": len(relazioni.get("livello_b2_responsabile_azione", []) or []),
        "n_timeline": len(cronistoria.get("timeline_decisioni_cluster1", []) or []),
        "n_possibili_aggiornamenti": len(cronistoria.get("possibili_aggiornamenti_decisioni", []) or []),
        "n_avvisi": len(cronistoria.get("avvisi_qualita_dati", []) or []),
        "n_documenti": None,
        "n_cluster": None,
    }
    if catalogo:
        meta["n_documenti"] = catalogo.get("meta", {}).get("n_documents")
        meta["n_cluster"] = catalogo.get("meta", {}).get("n_clusters")
    return meta


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>__TITOLO__</title>
<style>
  :root {
    --persona: #2563eb; --sistema: #059669; --normativa: #d97706;
    --bg: #0f1115; --panel: #171a21; --panel2: #1e222b; --border: #2a2f3a;
    --text: #e6e8ec; --muted: #9aa3b2; --accent: #f59e0b;
  }
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--text); }
  header { padding: 14px 20px; border-bottom: 1px solid var(--border); background: var(--panel);
           display:flex; align-items:baseline; gap:18px; flex-wrap:wrap; }
  header h1 { font-size: 17px; margin:0; font-weight:600; }
  header .meta { font-size: 12.5px; color: var(--muted); }
  header .meta b { color: var(--text); }
  nav.tabs { display:flex; gap:4px; padding: 0 16px; background: var(--panel); border-bottom: 1px solid var(--border);
             overflow-x:auto; }
  nav.tabs button { background: transparent; border:none; color: var(--muted); padding: 10px 14px;
                     font-size: 13px; cursor:pointer; border-bottom: 2px solid transparent; white-space:nowrap; }
  nav.tabs button.active { color: var(--text); border-bottom-color: var(--accent); }
  nav.tabs button:hover { color: var(--text); }
  main { padding: 16px 20px; }
  .tabpane { display:none; }
  .tabpane.active { display:block; }
  .graph-wrap { display:flex; gap:14px; }
  .graph-controls { width: 250px; flex: 0 0 250px; background: var(--panel); border:1px solid var(--border);
                     border-radius:8px; padding:12px; font-size:13px; }
  .graph-controls h3 { font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
                        margin: 14px 0 6px; }
  .graph-controls h3:first-child { margin-top:0; }
  .graph-controls label { display:flex; align-items:center; gap:6px; margin:4px 0; cursor:pointer; }
  .graph-controls input[type=text] { width:100%; padding:6px 8px; border-radius:6px; border:1px solid var(--border);
                     background: var(--panel2); color: var(--text); font-size:13px; }
  .graph-controls input[type=range] { width:100%; }
  .legend-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }
  #canvasHost { flex:1; position:relative; background: var(--panel); border:1px solid var(--border); border-radius:8px;
                overflow:hidden; height: 620px; }
  canvas { display:block; cursor: grab; }
  #sidepanel { position:absolute; top:10px; right:10px; width:280px; max-height: 96%; overflow:auto;
               background: rgba(23,26,33,.97); border:1px solid var(--border); border-radius:8px; padding:12px;
               font-size:12.5px; display:none; }
  #sidepanel h4 { margin:0 0 4px; font-size:14px; }
  #sidepanel .tag { display:inline-block; padding:1px 6px; border-radius:10px; font-size:10.5px; margin-bottom:6px; }
  #sidepanel .menzione { border-top:1px solid var(--border); padding:6px 0; }
  #sidepanel .menzione .doc { color: var(--accent); font-size:11.5px; }
  #sidepanel .menzione .ctx { color: var(--muted); font-size:11.5px; }
  #sidepanel .close { position:absolute; top:8px; right:10px; cursor:pointer; color:var(--muted); }
  table.dt { width:100%; border-collapse: collapse; font-size:13px; }
  table.dt th { text-align:left; color: var(--muted); font-weight:500; font-size:11.5px; text-transform:uppercase;
                letter-spacing:.03em; padding:6px 8px; border-bottom:1px solid var(--border); position:sticky; top:0;
                background: var(--bg); cursor:pointer; }
  table.dt td { padding:6px 8px; border-bottom:1px solid var(--border); vertical-align:top; }
  table.dt tr:hover td { background: var(--panel2); }
  .filters-row { display:flex; gap:10px; margin-bottom:10px; flex-wrap:wrap; align-items:center; }
  .filters-row input[type=text] { padding:6px 10px; border-radius:6px; border:1px solid var(--border);
                     background: var(--panel2); color: var(--text); font-size:13px; min-width:220px; }
  .pill { display:inline-block; padding:1px 8px; border-radius:10px; font-size:11px; }
  .pill.persona { background: color-mix(in srgb, var(--persona) 25%, transparent); color: #93b4fb; }
  .pill.sistema_tool { background: color-mix(in srgb, var(--sistema) 25%, transparent); color: #6ee7b7; }
  .pill.riferimento_normativo { background: color-mix(in srgb, var(--normativa) 25%, transparent); color: #fbbf24; }
  .card { background: var(--panel); border:1px solid var(--border); border-radius:8px; padding:12px 14px; margin-bottom:10px; }
  .card h4 { margin:0 0 6px; font-size:14px; }
  .conf { font-size:11px; padding:1px 7px; border-radius:10px; margin-left:8px; }
  .conf.bassa { background:#7f1d1d55; color:#fca5a5; }
  .conf.media { background:#78350f55; color:#fcd34d; }
  .conf.media-alta { background:#1e3a8a55; color:#93c5fd; }
  .conf.alta { background:#14532d55; color:#86efac; }
  .step { border-left: 2px solid var(--border); padding-left: 10px; margin: 6px 0 6px 4px; font-size:13px; color: var(--muted); }
  .step b { color: var(--text); }
  .empty { color: var(--muted); font-size:13px; padding: 20px 0; }
  .doc-code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size:11.5px; color: var(--muted); }
</style>
</head>
<body>
<header>
  <h1>__TITOLO__</h1>
  <span class="meta">generato il <b>__GENERATO_IL__</b></span>
  <span class="meta">__PERIMETRO__</span>
  <span class="meta"><b>__N_ENTITA__</b> entità · <b>__N_ARCHI_A__</b> co-menzioni · <b>__N_B1__</b> ruoli dichiarati ·
    <b>__N_B2__</b> azioni con responsabile</span>
</header>
<nav class="tabs">
  <button class="tab-btn active" data-tab="grafo">Grafo entità</button>
  <button class="tab-btn" data-tab="entita">Entità</button>
  <button class="tab-btn" data-tab="relazioni">Relazioni dichiarate</button>
  <button class="tab-btn" data-tab="timeline">Timeline decisioni</button>
  <button class="tab-btn" data-tab="aggiornamenti">Possibili aggiornamenti</button>
  <button class="tab-btn" data-tab="avvisi">Avvisi qualità dati</button>
</nav>
<main>

  <section class="tabpane active" id="tab-grafo">
    <div class="graph-wrap">
      <div class="graph-controls">
        <h3>Ricerca</h3>
        <input type="text" id="search" placeholder="cerca un'entità...">

        <h3>Tipo entità</h3>
        <label><input type="checkbox" class="tipo-cb" value="persona" checked>
          <span class="legend-dot" style="background:var(--persona)"></span> Persone</label>
        <label><input type="checkbox" class="tipo-cb" value="sistema_tool" checked>
          <span class="legend-dot" style="background:var(--sistema)"></span> Sistemi/tool</label>
        <label><input type="checkbox" class="tipo-cb" value="riferimento_normativo" checked>
          <span class="legend-dot" style="background:var(--normativa)"></span> Riferimenti normativi</label>

        <h3>Peso minimo co-menzione</h3>
        <input type="range" id="pesoMin" min="1" max="12" value="2">
        <div class="meta" id="pesoMinLabel">≥ 2 documenti condivisi</div>

        <h3>Isolati</h3>
        <label><input type="checkbox" id="hideIsolated" checked> Nascondi entità senza archi visibili</label>

        <h3>Info</h3>
        <div class="meta">Trascina i nodi per riorganizzare il grafo. Clicca un nodo per vedere le sue menzioni.
        Il grafo mostra solo il Livello A (co-occorrenza documentale, non implica relazione causale) —
        i ruoli/azioni dichiarati esplicitamente sono nella tab "Relazioni dichiarate".</div>
      </div>
      <div id="canvasHost">
        <canvas id="graphCanvas"></canvas>
        <div id="sidepanel"><span class="close" id="sidepanelClose">✕</span><div id="sidepanelBody"></div></div>
      </div>
    </div>
  </section>

  <section class="tabpane" id="tab-entita">
    <div class="filters-row">
      <input type="text" id="entitaSearch" placeholder="filtra per nome o alias...">
    </div>
    <div style="max-height:640px; overflow:auto;">
      <table class="dt" id="entitaTable">
        <thead><tr>
          <th data-k="nome">Nome canonico</th><th data-k="tipo">Tipo</th><th data-k="alias">Alias</th>
          <th data-k="n_menzioni">Menzioni</th><th data-k="ultima">Ultima menzione</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <section class="tabpane" id="tab-relazioni">
    <h3 style="color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.03em;">
      Livello B1 — ruolo dichiarato nel testo</h3>
    <div class="filters-row"><input type="text" id="b1Search" placeholder="filtra per persona o ruolo..."></div>
    <div style="max-height:280px; overflow:auto; margin-bottom:22px;">
      <table class="dt" id="b1Table">
        <thead><tr><th>Persona</th><th>Ruolo/responsabilità (testo libero)</th><th>Documento</th><th>Data</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <h3 style="color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.03em;">
      Livello B2 — responsabile generico → azione</h3>
    <div class="meta" style="margin-bottom:8px;">"Responsabile" è un'etichetta di ruolo generica come scritta nel
      documento (es. "Data Owner e Data Steward"), non una persona nominativa del Knowledge Layer.</div>
    <div class="filters-row"><input type="text" id="b2Search" placeholder="filtra per responsabile o azione..."></div>
    <div style="max-height:280px; overflow:auto;">
      <table class="dt" id="b2Table">
        <thead><tr><th>Responsabile (ruolo)</th><th>Azione</th><th>Documento</th><th>Data</th><th>Scadenza</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <section class="tabpane" id="tab-timeline">
    <div id="timelineList"></div>
  </section>

  <section class="tabpane" id="tab-aggiornamenti">
    <div id="aggiornamentiList"></div>
  </section>

  <section class="tabpane" id="tab-avvisi">
    <div id="avvisiList"></div>
  </section>

</main>

<script>
const DATA = __DATA_JSON__;

// ---------------------------------------------------------------------
// Navigazione tab
// ---------------------------------------------------------------------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tabpane").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "grafo") resizeCanvas();
  });
});

function esc(s) { const d = document.createElement("div"); d.textContent = (s == null ? "" : String(s)); return d.innerHTML; }

// ---------------------------------------------------------------------
// Tab Entità
// ---------------------------------------------------------------------
let entitaSort = {k: "n_menzioni", dir: -1};
function renderEntitaTable() {
  const q = document.getElementById("entitaSearch").value.trim().toLowerCase();
  let rows = DATA.nodes.filter(n => !q || n.nome.toLowerCase().includes(q) ||
    (n.alias || []).some(a => a.toLowerCase().includes(q)));
  rows.sort((a, b) => {
    let av = a[entitaSort.k], bv = b[entitaSort.k];
    if (entitaSort.k === "ultima") { av = a.ultima_menzione ? a.ultima_menzione.data || "" : ""; bv = b.ultima_menzione ? b.ultima_menzione.data || "" : ""; }
    if (typeof av === "string") return entitaSort.dir * av.localeCompare(bv);
    return entitaSort.dir * ((av||0) - (bv||0));
  });
  const tbody = document.querySelector("#entitaTable tbody");
  tbody.innerHTML = rows.map(n => `<tr>
    <td>${esc(n.nome)}</td>
    <td><span class="pill ${n.tipo}">${esc(n.tipo)}</span></td>
    <td>${esc((n.alias||[]).join(", "))}</td>
    <td>${n.n_menzioni}</td>
    <td>${n.ultima_menzione ? esc(n.ultima_menzione.data) + " <span class=doc-code>(" + esc(n.ultima_menzione.documento) + ")</span>" : "—"}</td>
  </tr>`).join("") || `<tr><td colspan=5 class=empty>Nessuna entità corrisponde al filtro.</td></tr>`;
}
document.getElementById("entitaSearch").addEventListener("input", renderEntitaTable);
document.querySelectorAll("#entitaTable th").forEach(th => th.addEventListener("click", () => {
  const k = th.dataset.k; if (!k) return;
  entitaSort.dir = (entitaSort.k === k) ? -entitaSort.dir : -1;
  entitaSort.k = k; renderEntitaTable();
}));

// ---------------------------------------------------------------------
// Tab Relazioni dichiarate (B1 / B2)
// ---------------------------------------------------------------------
function renderB1() {
  const q = document.getElementById("b1Search").value.trim().toLowerCase();
  const rows = DATA.b1.filter(r => !q || r.persona.toLowerCase().includes(q) || r.ruolo.toLowerCase().includes(q));
  document.querySelector("#b1Table tbody").innerHTML = rows.map(r => `<tr>
    <td>${esc(r.persona)}</td><td>${esc(r.ruolo)}</td>
    <td class="doc-code">${esc(r.documento)}</td><td>${esc(r.data)}</td>
  </tr>`).join("") || `<tr><td colspan=4 class=empty>Nessun risultato.</td></tr>`;
}
function renderB2() {
  const q = document.getElementById("b2Search").value.trim().toLowerCase();
  const rows = DATA.b2.filter(r => !q || r.responsabile.toLowerCase().includes(q) || r.azione.toLowerCase().includes(q));
  document.querySelector("#b2Table tbody").innerHTML = rows.map(r => `<tr>
    <td>${esc(r.responsabile)}</td><td>${esc(r.azione)}</td>
    <td class="doc-code">${esc(r.documento)}</td><td>${esc(r.data)}</td><td>${esc(r.scadenza)}</td>
  </tr>`).join("") || `<tr><td colspan=5 class=empty>Nessun risultato.</td></tr>`;
}
document.getElementById("b1Search").addEventListener("input", renderB1);
document.getElementById("b2Search").addEventListener("input", renderB2);

// ---------------------------------------------------------------------
// Tab Timeline
// ---------------------------------------------------------------------
function renderTimeline() {
  const el = document.getElementById("timelineList");
  if (!DATA.timeline.length) { el.innerHTML = '<div class="empty">Nessuna voce in timeline.</div>'; return; }
  el.innerHTML = DATA.timeline.map(t => `<div class="card">
      <h4>${esc(t.data)} <span class="doc-code">— ${esc(t.documento)}</span></h4>
      <div class="meta" style="margin-bottom:6px;">fonte data: ${esc(t.fonte_data)}</div>
      ${ (t.decisioni && t.decisioni.length) ? "<ul>" + t.decisioni.map(d => `<li>${esc(d)}</li>`).join("") + "</ul>"
         : '<div class="meta">(nessuna decisione estratta)</div>' }
    </div>`).join("");
}

// ---------------------------------------------------------------------
// Tab Possibili aggiornamenti
// ---------------------------------------------------------------------
function renderAggiornamenti() {
  const el = document.getElementById("aggiornamentiList");
  if (!DATA.aggiornamenti.length) { el.innerHTML = '<div class="empty">Nessuna voce.</div>'; return; }
  el.innerHTML = DATA.aggiornamenti.map(a => {
    const confClass = (a.confidenza || "").toLowerCase().replace(" ", "-");
    let steps = "";
    if (a.decisione_precedente) steps += `<div class="step"><b>${esc(a.decisione_precedente.data)}</b> (${esc(a.decisione_precedente.documento)}): ${esc(a.decisione_precedente.testo)}</div>`;
    if (a.decisione_successiva) steps += `<div class="step"><b>${esc(a.decisione_successiva.data)}</b> (${esc(a.decisione_successiva.documento)}): ${esc(a.decisione_successiva.testo)}</div>`;
    if (a.eseguita_in) steps += `<div class="step"><b>${esc(a.eseguita_in.data)}</b> (${esc(a.eseguita_in.documento)}): ${esc(a.eseguita_in.testo)}</div>`;
    if (a.evoluzione) steps += a.evoluzione.map(e => `<div class="step"><b>${esc(e.data)}</b> (${esc(e.documento)}): ${esc(e.stato)}</div>`).join("");
    return `<div class="card"><h4>${esc(a.tema)}<span class="conf ${confClass}">${esc(a.confidenza||"")}</span></h4>
      ${steps}
      ${a.nota ? `<div class="meta" style="margin-top:6px;">${esc(a.nota)}</div>` : ""}
    </div>`;
  }).join("");
}

// ---------------------------------------------------------------------
// Tab Avvisi qualità dati
// ---------------------------------------------------------------------
function renderAvvisi() {
  const el = document.getElementById("avvisiList");
  if (!DATA.avvisi.length) { el.innerHTML = '<div class="empty">Nessun avviso.</div>'; return; }
  el.innerHTML = DATA.avvisi.map(a => `<div class="card">
      <h4>${a.tipo ? `<span class="pill" style="background:#3f3f4655;color:#d1d5db;">${esc(a.tipo)}</span>` : ""}</h4>
      <div style="margin:4px 0 6px;">${esc(a.descrizione)}</div>
      <div class="meta">${(a.documenti || []).map(d => `<span class="doc-code">${esc(d)}</span>`).join(" · ")}</div>
    </div>`).join("");
}

renderEntitaTable(); renderB1(); renderB2(); renderTimeline(); renderAggiornamenti(); renderAvvisi();

// ---------------------------------------------------------------------
// Grafo entità — simulazione a forze in vanilla JS (nessuna libreria esterna)
// ---------------------------------------------------------------------
const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");
const sidepanel = document.getElementById("sidepanel");
const sidepanelBody = document.getElementById("sidepanelBody");
document.getElementById("sidepanelClose").addEventListener("click", () => sidepanel.style.display = "none");

const COLORS = { persona: "#2563eb", sistema_tool: "#059669", riferimento_normativo: "#d97706" };

let nodesById = {};
DATA.nodes.forEach(n => { nodesById[n.id] = n; });

let simNodes = DATA.nodes.map(n => ({
  id: n.id, tipo: n.tipo, nome: n.nome, n_menzioni: n.n_menzioni,
  x: (Math.random() - 0.5) * 400, y: (Math.random() - 0.5) * 400, vx: 0, vy: 0, fixed: false
}));
let simNodesById = {}; simNodes.forEach(n => simNodesById[n.id] = n);
let allEdges = DATA.edges_a;

let visibleNodes = [], visibleEdges = [];
let selectedNodeId = null, hoverNodeId = null;
let cameraX = 0, cameraY = 0, cameraZoom = 1;

function applyFilters() {
  const tiposOn = new Set(Array.from(document.querySelectorAll(".tipo-cb:checked")).map(cb => cb.value));
  const pesoMin = parseInt(document.getElementById("pesoMin").value, 10);
  const hideIso = document.getElementById("hideIsolated").checked;
  const q = document.getElementById("search").value.trim().toLowerCase();

  visibleEdges = allEdges.filter(e => e.peso >= pesoMin &&
    tiposOn.has(nodesById[e.source].tipo) && tiposOn.has(nodesById[e.target].tipo));

  const connected = new Set();
  visibleEdges.forEach(e => { connected.add(e.source); connected.add(e.target); });

  visibleNodes = simNodes.filter(n => {
    if (!tiposOn.has(n.tipo)) return false;
    if (hideIso && !connected.has(n.id)) return false;
    return true;
  });

  visibleNodes.forEach(n => { n._match = q && n.nome.toLowerCase().includes(q); });
}

["change","input"].forEach(evt => {
  document.querySelectorAll(".tipo-cb").forEach(cb => cb.addEventListener(evt, applyFilters));
  document.getElementById("pesoMin").addEventListener(evt, () => {
    document.getElementById("pesoMinLabel").textContent = "≥ " + document.getElementById("pesoMin").value + " documenti condivisi";
    applyFilters();
  });
  document.getElementById("hideIsolated").addEventListener(evt, applyFilters);
  document.getElementById("search").addEventListener(evt, applyFilters);
});

function resizeCanvas() {
  const host = document.getElementById("canvasHost");
  canvas.width = host.clientWidth; canvas.height = host.clientHeight;
}
window.addEventListener("resize", resizeCanvas);

function step() {
  const W = canvas.width, H = canvas.height;
  const centerX = 0, centerY = 0;
  const n = visibleNodes.length;
  // repulsione tra tutte le coppie visibili
  for (let i = 0; i < n; i++) {
    const a = visibleNodes[i];
    if (a.fixed) continue;
    let fx = 0, fy = 0;
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      const b = visibleNodes[j];
      let dx = a.x - b.x, dy = a.y - b.y;
      let d2 = dx*dx + dy*dy + 0.01;
      let d = Math.sqrt(d2);
      const rep = 1800 / d2;
      fx += (dx/d) * rep; fy += (dy/d) * rep;
    }
    // attrazione al centro (debole)
    fx += -a.x * 0.006; fy += -a.y * 0.006;
    a.vx = (a.vx + fx * 0.02) * 0.82;
    a.vy = (a.vy + fy * 0.02) * 0.82;
  }
  // molle sugli archi visibili
  visibleEdges.forEach(e => {
    const a = simNodesById[e.source], b = simNodesById[e.target];
    if (!a || !b) return;
    let dx = b.x - a.x, dy = b.y - a.y;
    let d = Math.sqrt(dx*dx + dy*dy) || 1;
    const target = 70 + 30 / Math.min(e.peso, 6);
    const f = (d - target) * 0.02;
    const ux = dx / d, uy = dy / d;
    if (!a.fixed) { a.vx += ux * f; a.vy += uy * f; }
    if (!b.fixed) { b.vx -= ux * f; b.vy -= uy * f; }
  });
  visibleNodes.forEach(a => { if (!a.fixed) { a.x += a.vx; a.y += a.vy; } });
}

function draw() {
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.save();
  ctx.translate(W/2 + cameraX, H/2 + cameraY);
  ctx.scale(cameraZoom, cameraZoom);

  ctx.lineWidth = 1;
  visibleEdges.forEach(e => {
    const a = simNodesById[e.source], b = simNodesById[e.target];
    if (!a || !b) return;
    const alpha = Math.min(0.08 + e.peso * 0.05, 0.65);
    ctx.strokeStyle = `rgba(148,163,184,${alpha})`;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  });

  visibleNodes.forEach(n => {
    const r = 4 + Math.min(Math.sqrt(n.n_menzioni) * 1.6, 12);
    const isSel = n.id === selectedNodeId, isHov = n.id === hoverNodeId;
    ctx.beginPath();
    ctx.arc(n.x, n.y, isSel ? r + 3 : r, 0, Math.PI * 2);
    ctx.fillStyle = COLORS[n.tipo] || "#888";
    ctx.globalAlpha = n._match === false && document.getElementById("search").value.trim() ? 0.25 : 1;
    ctx.fill();
    if (isSel || isHov) { ctx.lineWidth = 2; ctx.strokeStyle = "#f59e0b"; ctx.stroke(); }
    if (n._match || isSel || isHov) {
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#e6e8ec"; ctx.font = "12px sans-serif";
      ctx.fillText(n.nome, n.x + r + 4, n.y + 4);
    }
    ctx.globalAlpha = 1;
  });
  ctx.restore();
}

function loop() { step(); draw(); requestAnimationFrame(loop); }

function worldPos(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  const W = canvas.width, H = canvas.height;
  const x = (clientX - rect.left - W/2 - cameraX) / cameraZoom;
  const y = (clientY - rect.top - H/2 - cameraY) / cameraZoom;
  return {x, y};
}
function nodeAt(clientX, clientY) {
  const {x, y} = worldPos(clientX, clientY);
  let best = null, bestD = 16;
  visibleNodes.forEach(n => {
    const d = Math.hypot(n.x - x, n.y - y);
    if (d < bestD) { bestD = d; best = n; }
  });
  return best;
}

let dragNode = null, panning = false, panStart = null;
canvas.addEventListener("mousedown", e => {
  const n = nodeAt(e.clientX, e.clientY);
  if (n) { dragNode = n; n.fixed = true; canvas.style.cursor = "grabbing"; }
  else { panning = true; panStart = {x: e.clientX - cameraX, y: e.clientY - cameraY}; canvas.style.cursor = "grabbing"; }
});
canvas.addEventListener("mousemove", e => {
  if (dragNode) {
    const {x, y} = worldPos(e.clientX, e.clientY);
    dragNode.x = x; dragNode.y = y;
  } else if (panning) {
    cameraX = e.clientX - panStart.x; cameraY = e.clientY - panStart.y;
  } else {
    const n = nodeAt(e.clientX, e.clientY);
    hoverNodeId = n ? n.id : null;
    canvas.style.cursor = n ? "pointer" : "grab";
  }
});
window.addEventListener("mouseup", () => {
  if (dragNode) dragNode.fixed = false;
  dragNode = null; panning = false; canvas.style.cursor = "grab";
});
canvas.addEventListener("click", e => {
  if (panning) return;
  const n = nodeAt(e.clientX, e.clientY);
  if (n) openSidepanel(n.id);
});
canvas.addEventListener("wheel", e => {
  e.preventDefault();
  const delta = e.deltaY < 0 ? 1.08 : 0.92;
  cameraZoom = Math.min(Math.max(cameraZoom * delta, 0.2), 4);
}, {passive:false});

function openSidepanel(id) {
  selectedNodeId = id;
  const ent = nodesById[id];
  if (!ent) return;
  const rel = allEdges.filter(e => e.source === id || e.target === id)
    .sort((a,b) => b.peso - a.peso).slice(0, 12)
    .map(e => {
      const otherId = e.source === id ? e.target : e.source;
      const other = nodesById[otherId];
      return `<div class="step"><b>${esc(other ? other.nome : otherId)}</b> — peso ${e.peso}
        <div class="meta">${(e.documenti||[]).slice(0,3).map(d=>esc(d)).join(", ")}</div></div>`;
    }).join("");
  sidepanelBody.innerHTML = `
    <h4>${esc(ent.nome)}</h4>
    <span class="pill ${ent.tipo}">${esc(ent.tipo)}</span>
    ${ (ent.alias||[]).length ? `<div class="meta" style="margin-top:6px;">alias: ${esc(ent.alias.join(", "))}</div>` : "" }
    <h3 style="margin-top:12px;">Menzioni (${ent.menzioni.length})</h3>
    ${ ent.menzioni.slice(0,15).map(m => `<div class="menzione">
        <div class="doc">${esc(m.documento)}</div>
        <div class="meta">${esc(m.data)} · ${esc(m.tipo_documento)}</div>
        <div class="ctx">${esc(m.contesto)}</div>
      </div>`).join("") || '<div class="meta">nessuna</div>' }
    ${ rel ? `<h3 style="margin-top:12px;">Co-menzionato con</h3>${rel}` : "" }
  `;
  sidepanel.style.display = "block";
}

applyFilters();
resizeCanvas();
requestAnimationFrame(loop);
</script>
</body>
</html>
"""


def render_html(meta, nodes, edges_a, b1, b2, timeline, aggiornamenti, avvisi, titolo):
    data = {
        "nodes": nodes,
        "edges_a": edges_a,
        "b1": b1,
        "b2": b2,
        "timeline": timeline,
        "aggiornamenti": aggiornamenti,
        "avvisi": avvisi,
    }
    perimetro = ""
    if meta.get("n_documenti") is not None:
        perimetro = f"{meta['n_documenti']} documenti · {meta.get('n_cluster')} cluster nel catalogo"

    out = HTML_TEMPLATE
    out = out.replace("__TITOLO__", html_lib.escape(titolo))
    out = out.replace("__GENERATO_IL__", meta["generato_il"])
    out = out.replace("__PERIMETRO__", html_lib.escape(perimetro))
    out = out.replace("__N_ENTITA__", str(meta["n_entita_totali"]))
    out = out.replace("__N_ARCHI_A__", str(meta["n_archi_a"]))
    out = out.replace("__N_B1__", str(meta["n_archi_b1"]))
    out = out.replace("__N_B2__", str(meta["n_archi_b2"]))
    data_json = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
    out = out.replace("__DATA_JSON__", data_json)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge-layer", required=True)
    ap.add_argument("--relazioni", required=True)
    ap.add_argument("--cronistoria", required=True)
    ap.add_argument("--catalogo", help="opzionale, solo per i numeri di perimetro in testa alla pagina")
    ap.add_argument("--output", required=True)
    ap.add_argument("--titolo", default="Knowledge Base ETL Documentale")
    args = ap.parse_args()

    kl = load_json(args.knowledge_layer) or {}
    relazioni = load_json(args.relazioni) or {}
    cronistoria = load_json(args.cronistoria) or {}
    catalogo = load_json(args.catalogo)

    nodes = build_nodes_and_edges(kl)
    edges_a = build_edges_a(relazioni)
    b1 = build_b1(relazioni)
    b2 = build_b2(relazioni)
    timeline = cronistoria.get("timeline_decisioni_cluster1", []) or []
    aggiornamenti = cronistoria.get("possibili_aggiornamenti_decisioni", []) or []
    avvisi = cronistoria.get("avvisi_qualita_dati", []) or []

    meta = build_meta(kl, relazioni, cronistoria, catalogo, args.titolo)
    html_out = render_html(meta, nodes, edges_a, b1, b2, timeline, aggiornamenti, avvisi, args.titolo)

    Path(args.output).write_text(html_out, encoding="utf-8")
    print(f"Scritto: {args.output}")
    print(f"Entità: {meta['n_entita_totali']} (persone {meta['n_persone']}, sistemi/tool {meta['n_sistemi_tool']}, "
          f"normative {meta['n_riferimenti_normativi']})")
    print(f"Archi livello A: {meta['n_archi_a']} | B1: {meta['n_archi_b1']} | B2: {meta['n_archi_b2']}")


if __name__ == "__main__":
    main()
