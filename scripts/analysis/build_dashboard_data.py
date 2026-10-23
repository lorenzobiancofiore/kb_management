#!/usr/bin/env python3
"""
Prepara i dati per la dashboard della knowledge base ETL documentale.

Legge i JSON di una cartella `Output/ETL_Documentale` e scrive due file
pronti per essere pubblicati accanto alla pagina `dashboard/dashboard.html`:

  <out>/data/kb.json     KB compatta (estrazione, knowledge layer, cronistoria,
                         catalogo senza centroidi, relazioni B1/B2, correzioni)
                         + statistiche calcolate + avvisi con id e stato
  (kb.json contiene anche `discordanze`, da discordanze_pilota.json)
  <out>/data/stato.json  copia di `stato_ultima_elaborazione.json` (esito
                         dell'ultima elaborazione, storico)

Non modifica mai i file della KB. Nessuna dipendenza oltre la libreria standard.

Uso:
    python3 build_dashboard_data.py --etl-dir "<.../Output/ETL_Documentale>" --out-dir <cartella di scratch>

Stato degli avvisi (campo `stato`):
  gestito       ha il campo `gestione`, oppure il testo riporta una conferma/risoluzione
  da_gestire    richiede una decisione di una persona (identificazioni incerte,
                abbreviazioni ambigue, incoerenze di data, ...)
  informativo   segnalazione che non richiede azione (duplicati, esclusioni, ...)
La pagina mostra comunque tutto e permette di rispondere; una risposta applicata
dall'aggiornamento giornaliero porta l'avviso a `gestito` (campo `gestione`).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone

AZIONE = {
    "identificazione_incerta_persona", "abbreviazione_ambigua_sistema_tool",
    "variante_nome_persona", "variante_nome_sistema_tool", "incoerenza_data",
    "classificazione_incerta_avanzamento_vs_contenuto", "template_senza_data",
    "ruolo_generico_non_persona", "possibile_origine_anteriore_tema_tracciato",
    "possibile_aggiornamento_tema_non_incorporato",
}
MARCATORI_GESTITO = ("confermat", "risolto", "rettifica", "[risolto")


def nfc(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().lower()


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def avviso_id(a):
    base = (a.get("tipo") or "") + "|" + (a.get("descrizione") or "")[:80]
    return "av-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]


def classifica_avviso(a):
    d = (a.get("descrizione") or "").lower()
    if a.get("gestione"):
        return "gestito"
    if any(m in d for m in MARCATORI_GESTITO):
        return "gestito"
    tipo = a.get("tipo")
    if tipo in AZIONE:
        return "da_gestire"
    if tipo is None and ("da verificare" in d or "da confermare" in d or "disallineamento" in d):
        return "da_gestire"
    return "informativo"


def passaggi(testo, target=700):
    """Spezza il testo in passaggi di ~target caratteri, rispettando le righe."""
    out, cur = [], ""
    for riga in re.split(r"\n+", testo):
        riga = riga.strip()
        if not riga:
            continue
        if cur and len(cur) + len(riga) + 1 > target:
            out.append(cur)
            cur = riga
        else:
            cur = (cur + " " + riga).strip()
    if cur:
        out.append(cur)
    return out


def scrivi_testi(args, cat, est, out):
    """Passaggi originali dei documenti elaborati (solo formati testuali) per il recupero in dashboard."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etl_pipeline"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from catalogazione import extract_text
    from pathlib import Path
    tipi = {t.strip().lower() for t in args.tipi.split(",") if t.strip()}
    estratti = {nfc(k): k for k in list(est.get("avanzamento", {})) + list(est.get("contenuto", {}))}
    res, tot = {}, 0
    for path in cat["documents"]:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext not in tipi or nfc(path) not in estratti:
            continue
        f = Path(args.source_root) / path
        if not f.exists():
            continue
        txt, _ = extract_text(f, ext)
        if not txt:
            continue
        ps = passaggi(txt[: args.max_chars])
        res[path] = {"p": ps, "t": len(txt) > args.max_chars}
        tot += sum(len(x) for x in ps)
    with open(os.path.join(out, "testi.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, separators=(",", ":"))
    print("testi.json", len(res), "documenti,", round(tot / 1024), "KB di testo")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etl-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--source-root", help="cartella dei documenti sorgente: se data, scrive data/testi.json con i passaggi originali per il recupero")
    ap.add_argument("--max-chars", type=int, default=20000, help="massimo di caratteri di testo per documento in testi.json")
    ap.add_argument("--tipi", default="docx,pdf,pptx,md,html,htm,txt", help="estensioni da includere in testi.json (tabelle xlsx/csv escluse)")
    args = ap.parse_args()
    E = args.etl_dir

    pick = lambda pat: (sorted(f for f in glob.glob(os.path.join(E, pat)) if ".bak" not in f) or [None])[-1]
    cat = load(pick("catalogo_*.json"), {"documents": {}, "clusters": {}})
    est = load(pick("estrazione_*.json"), {"avanzamento": {}, "contenuto": {}})
    kl = load(pick("knowledge_layer_*.json"), {"persone": [], "sistemi_tool": [], "riferimenti_normativi": []})
    cr = load(pick("cronistoria_*.json"), {})
    rel = load(pick("relazioni_*.json"), {})
    corr = load(pick("correzioni_*.json"), None)
    disc = load(os.path.join(E, "discordanze_pilota.json"), {"meta": {}, "discordanze": []})
    stato = load(os.path.join(E, "stato_ultima_elaborazione.json"), {
        "data_run": None, "tipo": None, "esito": "nessun_dato",
        "riepilogo": "Nessuna elaborazione registrata.", "storico": []})

    # ---- copertura e motivazioni dei non elaborati
    estratti = {nfc(k): k for k in list(est.get("avanzamento", {})) + list(est.get("contenuto", {}))}
    docs, non_elab = {}, []
    for path, d in cat["documents"].items():
        cl = cat["clusters"].get(d["cluster_id"], {})
        ok = nfc(path) in estratti
        docs[path] = {"c": d["cluster_id"], "s": d.get("extraction_status", ""), "e": ok}
        if ok:
            continue
        st = d.get("extraction_status", "")
        if cl.get("tipo") == "escluso_esercitazione":
            motivo = "Esercitazione o dati di corso, esclusi dal perimetro"
        elif "formato_non_supportato" in st:
            motivo = "Formato non supportato dall'estrattore (video, immagini, formati legacy)"
        elif st.startswith("solo_metadata") and "errore" in st:
            motivo = "File non apribile (errore di lettura)"
        else:
            motivo = "Non ancora estratto"
        non_elab.append({"documento": path, "cluster": d["cluster_id"], "cluster_label": cl.get("label", ""), "motivo": motivo})

    motivi = Counter(x["motivo"] for x in non_elab)
    per_cluster = []
    for cid, cl in cat["clusters"].items():
        tot = len(cl.get("documents", []))
        ex = sum(1 for p in cl.get("documents", []) if nfc(p) in estratti)
        per_cluster.append({"id": cid, "label": cl.get("label", ""), "tipo": cl.get("tipo"), "totale": tot, "estratti": ex})

    # ---- avvisi con id e stato
    avvisi = []
    for a in cr.get("avvisi_qualita_dati", []):
        b = dict(a)
        b["id"] = avviso_id(a)
        b["stato"] = classifica_avviso(a)
        avvisi.append(b)
    conta_av = Counter(a["stato"] for a in avvisi)

    # ---- relazioni: solo livelli B (il livello A pesa molto e non serve per interrogare)
    relB = {"b1": rel.get("livello_b1_ruolo_dichiarato", []), "b2": rel.get("livello_b2_responsabile_azione", []),
            "lineage": [{k: v for k, v in a.items() if k != "livello"} for a in rel.get("livello_b_lineage", [])]}

    # profili (campi, KPI, lineage, ingestione): vivono nel Knowledge Layer; in Estrazione restano solo come indice testuale
    profili_idx = {}
    for sec in ("avanzamento", "contenuto"):
        for doc, r in est.get(sec, {}).items():
            pr = r.pop("profilo", None)
            if not pr:
                continue
            t = []
            for o in pr.get("oggetti_dati", []):
                t.append(o.get("nome", "") + " " + " ".join(c.get("nome", "") for c in o.get("campi", [])[:80]))
            for rp in pr.get("report", []):
                t.append(rp.get("nome", "") + " " + " ".join(k.get("nome", "") for k in rp.get("kpi", [])))
            for g in pr.get("ingestione_sistema", []):
                t.append(g.get("sistema", ""))
            profili_idx[doc] = " ".join(t)[:6000]

    timeline = next((v for k, v in cr.items() if k.startswith("timeline_decisioni")), [])
    date_iso = [v["data"] for v in timeline if v.get("data") and re.match(r"^\d{4}-\d{2}-\d{2}$", str(v["data"]))]
    stats = {
        "generato_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documenti_indicizzati": len(cat["documents"]),
        "documenti_estratti": len(estratti),
        "estratti_avanzamento": len(est.get("avanzamento", {})),
        "estratti_contenuto": len(est.get("contenuto", {})),
        "non_elaborati": len(non_elab),
        "non_elaborati_per_motivo": [{"motivo": k, "n": v} for k, v in motivi.most_common()],
        "cluster": len(cat["clusters"]),
        "persone": len(kl.get("persone", [])),
        "sistemi_tool": len(kl.get("sistemi_tool", [])),
        "riferimenti_normativi": len(kl.get("riferimenti_normativi", [])),
        "menzioni": sum(len(e.get("menzioni", [])) for k in ("persone", "sistemi_tool", "riferimenti_normativi") for e in kl.get(k, [])),
        "timeline_voci": len(timeline),
        "timeline_dal": min(date_iso) if date_iso else None,
        "timeline_al": max(date_iso) if date_iso else None,
        "temi_tracciati": len(cr.get("possibili_aggiornamenti_decisioni", [])),
        "avvisi_totali": len(avvisi),
        "avvisi_da_gestire": conta_av.get("da_gestire", 0),
        "avvisi_gestiti": conta_av.get("gestito", 0),
        "avvisi_informativi": conta_av.get("informativo", 0),
        "archi_b1": len(relB["b1"]),
        "archi_b2": len(relB["b2"]),
        "archi_a": (rel.get("meta") or {}).get("n_archi_livello_a"),
        "oggetti_dati": len(kl.get("oggetti_dati", [])),
        "report": len(kl.get("report", [])),
        "ingestione_sistemi": len(kl.get("ingestione_sistema", [])),
        "archi_lineage": len(relB["lineage"]),
        "discordanze_aperte": sum(1 for d in disc.get("discordanze", []) if d.get("stato") == "aperta"),
        "discordanze_confermate": sum(1 for d in disc.get("discordanze", []) if d.get("stato") == "confermata"),
        "correzioni_attive": len([c for c in (corr or {}).get("correzioni", []) if not c.get("superata")]) if isinstance(corr, dict) else 0,
    }

    clusters = {cid: {"label": cl.get("label", ""), "tipo": cl.get("tipo"), "size": len(cl.get("documents", []))}
                for cid, cl in cat["clusters"].items()}
    kb = {
        "stats": stats,
        "per_cluster": per_cluster,
        "non_elaborati": non_elab,
        "clusters": clusters,
        "documents": docs,
        "estrazione": est,
        "profili_idx": profili_idx,
        "aree": {k: {"label": v.get("label"), "tipo": v.get("tipo"), "n": v.get("n_documenti")} for k, v in (cat.get("aree_proposte") or {}).items()},
        "kl": kl,
        "cronistoria": {
            "timeline": timeline,
            "temi": cr.get("possibili_aggiornamenti_decisioni", []),
            "avvisi": avvisi,
            "evoluzioni": cr.get("evoluzioni_rilevate", []),
        },
        "relazioni": relB,
        "discordanze": disc.get("discordanze", []),
        "correzioni": (corr or {}).get("correzioni", []) if isinstance(corr, dict) else (corr or []),
    }
    out = os.path.join(args.out_dir, "data")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "kb.json"), "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out, "stato.json"), "w", encoding="utf-8") as f:
        json.dump(stato, f, ensure_ascii=False, separators=(",", ":"))
    if args.source_root:
        scrivi_testi(args, cat, est, out)
    print("kb.json", round(os.path.getsize(os.path.join(out, "kb.json")) / 1024), "KB |",
          "estratti", stats["documenti_estratti"], "/", stats["documenti_indicizzati"],
          "| avvisi da gestire", stats["avvisi_da_gestire"], "| non elaborati", stats["non_elaborati"])


if __name__ == "__main__":
    main()
