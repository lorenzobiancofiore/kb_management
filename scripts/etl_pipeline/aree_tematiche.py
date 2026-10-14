#!/usr/bin/env python3
"""
Aree tematiche (overlay sui cluster) derivate dalla struttura delle cartelle.

I cluster TF-IDF restano com'sono. Questo script AGGIUNGE al catalogo un campo `aree_proposte`:
un raggruppamento dei documenti per cartella (2-3 livelli) con etichetta provvisoria e stato
"proposta_da_confermare". Serve a raggruppare i documenti per sistema/report/ambito quando
si risponde a domande su campi, KPI e lineage, e a facilitare lo split dei batch di Estrazione
(documenti dello stesso ambito nello stesso batch).

L'utente conferma o corregge etichette e tipi: lo script NON sovrascrive aree già presenti
con stato diverso da "proposta_da_confermare".

Uso:
    python3 aree_tematiche.py --catalogo catalogo_X.json [--livelli 2] [--profondi "Cartella1,Cartella2"]
      --livelli   profondità standard del raggruppamento (default 2)
      --profondi  cartelle di primo livello da raggruppare a 3 livelli (default: nessuna)
Opzioni: --solo-estratti  considera solo i documenti con extraction_status == "estratto".
"""
import argparse
import json
from pathlib import Path


def area_di(path, livelli, profondi):
    parti = path.split("/")
    if len(parti) <= 1:
        return "Radice"
    n = livelli + 1 if parti[0] in profondi else livelli
    return "/".join(parti[: min(n, len(parti) - 1)]) or parti[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", required=True)
    ap.add_argument("--livelli", type=int, default=2)
    ap.add_argument("--profondi", default="")
    ap.add_argument("--solo-estratti", action="store_true")
    a = ap.parse_args()
    profondi = {x.strip() for x in a.profondi.split(",") if x.strip()}
    p = Path(a.catalogo)
    cat = json.loads(p.read_text(encoding="utf-8"))
    aree = {}
    for doc, d in cat["documents"].items():
        if a.solo_estratti and d.get("extraction_status") != "estratto":
            continue
        aree.setdefault(area_di(doc, a.livelli, profondi), []).append(doc)
    esistenti = cat.get("aree_proposte", {})
    out = {}
    for k in sorted(aree):
        old = esistenti.get(k)
        if old and old.get("stato") != "proposta_da_confermare":
            old["documenti"], old["n_documenti"] = sorted(aree[k]), len(aree[k])
            out[k] = old
        else:
            out[k] = {"label": k.split("/")[-1], "tipo": None, "stato": "proposta_da_confermare",
                      "n_documenti": len(aree[k]), "documenti": sorted(aree[k])}
    cat["aree_proposte"] = out
    cat["aree_proposte_nota"] = ("Overlay per area tematica derivato dalla struttura delle cartelle. "
                                 "Non sostituisce i cluster TF-IDF; etichette e tipi da confermare con l'utente.")
    p.write_text(json.dumps(cat, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"{len(out)} aree scritte in {p}")
    for k, v in out.items():
        print(f"  {v['n_documenti']:4d}  {k}")


if __name__ == "__main__":
    main()
