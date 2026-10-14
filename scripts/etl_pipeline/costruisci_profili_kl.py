#!/usr/bin/env python3
"""
Profili (data model, reportistica, lineage, ingestione) -> Knowledge Layer + Relazioni.

Legge i campi `profilo` presenti in estrazione_*.json (fatti dichiarati nei documenti, nessuna inferenza)
e AGGIUNGE a knowledge_layer_*.json le liste:
  - oggetti_dati        (tabelle/viste/dataset) con campi aggregati per nome e documenti di provenienza
  - report              (report/dashboard) con KPI, logica di calcolo (versioni per documento, la più recente prima)
  - ingestione_sistema  (stato/modalità di ingestione per sistema, versioni per documento)
e AGGIUNGE a relazioni_*.json la lista `livello_b_lineage`:
  - fonte_dati_report   report  -> oggetto dati / fonte
  - origina_da_sistema  oggetto -> sistema
  - deriva_da           oggetto -> oggetto (join, fk, deriva_da dichiarati)
  - ingerito_da         sistema -> oggetto ingerito
Ogni arco porta documento ed evidenza. Un riferimento che non coincide con un'entità nota resta testo (`risolto: false`).

Va rilanciato DOPO ogni rigenerazione di Knowledge Layer e Relazioni (che riscrivono i due file da zero).
Generico: i file sono trovati per pattern nella cartella ETL_Documentale del progetto.
Uso: python3 costruisci_profili_kl.py --etl-dir "<.../Output/ETL_Documentale>"
"""
import argparse
import glob
import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def nf(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(s))).strip().lower()


def slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def pick(d, pattern):
    f = sorted(x for x in glob.glob(os.path.join(str(d), pattern)) if ".bak" not in x and "pre_profili" not in x)
    if not f:
        raise SystemExit(f"File non trovato: {pattern} in {d}")
    return Path(f[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etl-dir", default=".")
    d = Path(ap.parse_args().etl_dir)
    est_p, kl_p, rel_p = pick(d, "estrazione_*.json"), pick(d, "knowledge_layer_*.json"), pick(d, "relazioni_*.json")
    est = json.load(open(est_p, encoding="utf-8"))
    idx = json.load(open(pick(d, "index_*.json"), encoding="utf-8"))["documents"]
    kl = json.load(open(kl_p, encoding="utf-8"))
    rel = json.load(open(rel_p, encoding="utf-8"))
    idx_n = {nf(k): v for k, v in idx.items()}

    def doc_date(doc):
        e = idx_n.get(nf(doc), {})
        return (e.get("last_modified_at") or "")[:10]

    sistemi = {}
    for s in kl.get("sistemi_tool", []):
        sistemi[nf(s["nome_canonico"])] = s
        for a in s.get("alias", []):
            sistemi.setdefault(nf(a), s)

    docs = []
    for sec in ("avanzamento", "contenuto"):
        for doc, r in est[sec].items():
            if r.get("profilo"):
                docs.append((doc, sec, r["profilo"]))
    # più recenti prima
    docs.sort(key=lambda x: doc_date(x[0]), reverse=True)

    # ---------------- oggetti dati
    oggetti = {}
    for doc, sec, p in docs:
        for o in p.get("oggetti_dati", []):
            if not o.get("nome"):
                continue
            k = nf(o["nome"])
            e = oggetti.setdefault(k, {"id": "oggetto-" + slug(o["nome"]), "tipo": "oggetto_dati",
                                       "nome_canonico": o["nome"], "alias": [], "tipo_oggetto": o.get("tipo"),
                                       "sistema_origine": o.get("sistema_origine"), "descrizione": o.get("descrizione"),
                                       "campi": {}, "chiavi": [], "relazioni": [], "logica_filtri": o.get("logica_filtri"),
                                       "menzioni": [], "avvisi": [], "ultima_menzione": None})
            if o["nome"] != e["nome_canonico"] and o["nome"] not in e["alias"]:
                e["alias"].append(o["nome"])
            for f in ("tipo_oggetto", "sistema_origine", "descrizione", "logica_filtri"):
                src = o.get("tipo") if f == "tipo_oggetto" else o.get(f)
                if not e.get(f) and src:
                    e[f] = src
            for c in o.get("campi", []):
                if not c.get("nome"):
                    continue
                ck = nf(c["nome"])
                ce = e["campi"].get(ck)
                if ce is None:
                    ce = {"nome": c["nome"], "tipo": c.get("tipo"), "descrizione": c.get("descrizione"),
                          "chiave": bool(c.get("chiave")), "origine": c.get("origine"), "documenti": [],
                          "descrizioni_alternative": []}
                    e["campi"][ck] = ce
                else:
                    for f in ("tipo", "descrizione", "origine"):
                        if not ce.get(f) and c.get(f):
                            ce[f] = c[f]
                    if c.get("descrizione") and ce.get("descrizione") and nf(c["descrizione"]) != nf(ce["descrizione"]):
                        ce["descrizioni_alternative"].append({"documento": doc, "descrizione": c["descrizione"]})
                    ce["chiave"] = ce["chiave"] or bool(c.get("chiave"))
                if doc not in ce["documenti"]:
                    ce["documenti"].append(doc)
            for ch in o.get("chiavi", []):
                if ch not in e["chiavi"]:
                    e["chiavi"].append(ch)
            for r in o.get("relazioni", []):
                e["relazioni"].append(dict(r, documento=doc))
            for a in o.get("avvisi", []):
                e["avvisi"].append({"documento": doc, "avviso": a})
            e["menzioni"].append({"documento": doc, "tipo_documento": sec, "data": doc_date(doc) or None,
                                  "fonte_data": "data_modifica_file (approssimata)",
                                  "contesto": (o.get("descrizione") or "")[:200],
                                  "campi_nel_documento": len(o.get("campi", [])),
                                  "evidenza": o.get("evidenza")})
            if e["ultima_menzione"] is None:
                e["ultima_menzione"] = {"documento": doc, "data": doc_date(doc) or None}
    for e in oggetti.values():
        e["campi"] = list(e["campi"].values())
        e["n_campi"] = len(e["campi"])
        for c in e["campi"]:
            if not c["descrizioni_alternative"]:
                del c["descrizioni_alternative"]

    def risolvi_oggetto(txt):
        o = oggetti.get(nf(txt))
        return o

    # ---------------- report
    report = {}
    for doc, sec, p in docs:
        for r in p.get("report", []):
            if not r.get("nome"):
                continue
            k = nf(r["nome"])
            e = report.setdefault(k, {"id": "report-" + slug(r["nome"]), "tipo": "report", "nome_canonico": r["nome"],
                                      "alias": [], "scopo": r.get("scopo"), "versioni": [], "menzioni": [],
                                      "ultima_menzione": None})
            if r["nome"] != e["nome_canonico"] and r["nome"] not in e["alias"]:
                e["alias"].append(r["nome"])
            if not e.get("scopo") and r.get("scopo"):
                e["scopo"] = r["scopo"]
            e["versioni"].append({"documento": doc, "data": doc_date(doc) or None,
                                  "fonte_data": "data_modifica_file (approssimata)",
                                  "scopo": r.get("scopo"), "kpi": r.get("kpi", []),
                                  "fonti_dati": r.get("fonti_dati", []), "filtri_visuali": r.get("filtri_visuali", []),
                                  "stato": r.get("stato"), "evidenza": r.get("evidenza"), "avvisi": r.get("avvisi", [])})
            e["menzioni"].append({"documento": doc, "tipo_documento": sec, "data": doc_date(doc) or None,
                                  "fonte_data": "data_modifica_file (approssimata)",
                                  "contesto": (r.get("scopo") or "")[:200]})
            if e["ultima_menzione"] is None:
                e["ultima_menzione"] = {"documento": doc, "data": doc_date(doc) or None}
    for e in report.values():
        e["n_kpi"] = len({nf(k.get("nome", "")) for v in e["versioni"] for k in v["kpi"] if k.get("nome")})

    # ---------------- ingestione per sistema
    ingest = {}
    for doc, sec, p in docs:
        for g in p.get("ingestione_sistema", []):
            if not g.get("sistema"):
                continue
            k = nf(g["sistema"])
            e = ingest.setdefault(k, {"id": "ingestione-" + slug(g["sistema"]), "tipo": "ingestione_sistema",
                                      "nome_canonico": g["sistema"], "alias": [], "sistema_id": None,
                                      "versioni": [], "menzioni": [], "ultima_menzione": None})
            if g["sistema"] != e["nome_canonico"] and g["sistema"] not in e["alias"]:
                e["alias"].append(g["sistema"])
            s = sistemi.get(k)
            if s and not e["sistema_id"]:
                e["sistema_id"] = s["id"]
            e["versioni"].append({"documento": doc, "data": doc_date(doc) or None,
                                  "fonte_data": "data_modifica_file (approssimata)",
                                  "oggetti": g.get("oggetti", []), "modalita": g.get("modalita"),
                                  "frequenza": g.get("frequenza"), "stato": g.get("stato"), "note": g.get("note"),
                                  "evidenza": g.get("evidenza"), "avvisi": g.get("avvisi", [])})
            e["menzioni"].append({"documento": doc, "tipo_documento": sec, "data": doc_date(doc) or None,
                                  "fonte_data": "data_modifica_file (approssimata)",
                                  "contesto": f"stato: {g.get('stato') or 'n.d.'}; modalità: {g.get('modalita') or 'n.d.'}"})
            if e["ultima_menzione"] is None:
                e["ultima_menzione"] = {"documento": doc, "data": doc_date(doc) or None}

    # ---------------- lineage
    archi = []

    def nodo(txt, kind_hint=None):
        o = risolvi_oggetto(txt)
        if o:
            return {"id": o["id"], "tipo": "oggetto_dati", "nome_canonico": o["nome_canonico"], "risolto": True}
        s = sistemi.get(nf(txt))
        if s:
            return {"id": s["id"], "tipo": "sistema_tool", "nome_canonico": s["nome_canonico"], "risolto": True}
        r = report.get(nf(txt))
        if r:
            return {"id": r["id"], "tipo": "report", "nome_canonico": r["nome_canonico"], "risolto": True}
        return {"tipo": "testo_libero", "valore": txt, "risolto": False}

    seen = set()

    def add(tipo, da, a, doc, evid):
        key = (tipo, json.dumps(da, sort_keys=True), json.dumps(a, sort_keys=True), doc)
        if key in seen:
            return
        seen.add(key)
        archi.append({"livello": "B", "tipo_relazione": tipo, "da": da, "a": a, "documento": doc,
                      "data": doc_date(doc) or None, "evidenza_testuale": evid})

    for doc, sec, p in docs:
        for r in p.get("report", []):
            if not r.get("nome"):
                continue
            da = {"id": report[nf(r["nome"])]["id"], "tipo": "report", "nome_canonico": report[nf(r["nome"])]["nome_canonico"], "risolto": True}
            fonti = list(r.get("fonti_dati", [])) + [f for k in r.get("kpi", []) for f in k.get("fonti", [])]
            for f in dict.fromkeys(fonti):
                if f:
                    add("fonte_dati_report", da, nodo(f), doc, r.get("evidenza") or f"fonti_dati di {r['nome']}")
        for o in p.get("oggetti_dati", []):
            if not o.get("nome"):
                continue
            da = {"id": oggetti[nf(o["nome"])]["id"], "tipo": "oggetto_dati", "nome_canonico": oggetti[nf(o["nome"])]["nome_canonico"], "risolto": True}
            if o.get("sistema_origine"):
                add("origina_da_sistema", da, nodo(o["sistema_origine"]), doc, o.get("evidenza") or "sistema_origine")
            for rr in o.get("relazioni", []):
                if rr.get("con"):
                    add("deriva_da" if rr.get("tipo") == "deriva_da" else "join_con" if rr.get("tipo") == "join" else "fk_con",
                        da, nodo(rr["con"]), doc, rr.get("condizione") or o.get("evidenza") or "")
        for g in p.get("ingestione_sistema", []):
            if not g.get("sistema"):
                continue
            da = nodo(g["sistema"])
            for ob in g.get("oggetti", []):
                if ob:
                    add("ingerito_da", nodo(ob), da, doc, g.get("evidenza") or "ingestione_sistema")

    kl["oggetti_dati"] = sorted(oggetti.values(), key=lambda e: -e["n_campi"])
    kl["report"] = sorted(report.values(), key=lambda e: -len(e["versioni"]))
    kl["ingestione_sistema"] = sorted(ingest.values(), key=lambda e: -len(e["versioni"]))
    kl["meta"].update({"n_oggetti_dati": len(oggetti), "n_report": len(report), "n_ingestione_sistema": len(ingest),
                       "profili": "oggetti_dati/report/ingestione_sistema derivati da estrazione.profilo"})
    rel["livello_b_lineage"] = archi
    rel["meta"]["n_archi_livello_b_lineage"] = len(archi)
    json.dump(kl, open(kl_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(rel, open(rel_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ris = sum(1 for a in archi if a["a"].get("risolto"))
    print(f"oggetti {len(oggetti)} (campi {sum(e['n_campi'] for e in oggetti.values())}), report {len(report)}, "
          f"ingestione {len(ingest)}, archi lineage {len(archi)} (destinazione risolta {ris})")


if __name__ == "__main__":
    main()
