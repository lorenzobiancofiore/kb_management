#!/usr/bin/env python3
"""
Trova le knowledge base ETL documentali (Indicizzazione -> Catalogazione ->
Estrazione -> Knowledge Layer -> Cronistoria) sotto una cartella Progetti/,
e calcola quanto della copertura totale (catalogo) e' stato effettivamente
lavorato dalle fasi successive (estrazione/knowledge layer/cronistoria).

Questo e' il primo passo di qualsiasi interrogazione: prima di rispondere
a una domanda, bisogna sapere ESATTAMENTE quali cluster/documenti sono
dentro il perimetro gia' processato e quali no, perche' quasi sempre queste
pipeline vengono costruite in modo incrementale (un "pilota" su pochi
cluster, poi eventualmente estese). Rispondere ignorando questo confine
porta a risposte sicure ma sbagliate, o a risposte che sembrano complete
ma coprono solo una parte del corpus.

Uso:
    python3 locate_kb.py --root "/percorso/Progetti"
    python3 locate_kb.py --root "/percorso/Progetti" --project Governance
    python3 locate_kb.py --etl-dir "/percorso/Progetti/Governance/Output/ETL_Documentale"

Output: JSON su stdout con, per ogni ETL_Documentale trovata:
- i path dei file di ciascuna fase (se presenti) e del registro correzioni
  utente (`correzioni_*.json`), con il numero di correzioni attive
- meta del catalogo (n. cluster, n. documenti totali)
- quanti documenti/cluster sono coperti da estrazione/knowledge_layer/cronistoria
- elenco dei cluster NON (o solo parzialmente) coperti, con label e size,
  cosi' da poter avvisare l'utente se la domanda cade fuori dal perimetro
"""
import argparse
import glob
import json
import os


def find_etl_dirs(root):
    """Cerca cartelle 'ETL_Documentale' sotto root (di solito dentro
    Progetti/<Nome>/Output/)."""
    return sorted(glob.glob(os.path.join(root, "**", "ETL_Documentale"), recursive=True))


def pick_file(etl_dir, patterns):
    """Ritorna il primo file trovato che matcha uno dei glob pattern,
    escludendo i backup (.bak*)."""
    for pat in patterns:
        matches = sorted(
            f for f in glob.glob(os.path.join(etl_dir, pat))
            if ".bak" not in os.path.basename(f)
        )
        if matches:
            # se ce ne sono piu' d'uno, quello con mtime piu' recente
            return max(matches, key=os.path.getmtime)
    return None


def load_json(path):
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"_errore_lettura": str(e)}


def analyze_etl_dir(etl_dir):
    files = {
        "index": pick_file(etl_dir, ["index_*.json"]),
        "catalogo": pick_file(etl_dir, ["catalogo_*.json"]),
        "estrazione": pick_file(etl_dir, ["estrazione_*.json"]),
        "knowledge_layer": pick_file(etl_dir, ["knowledge_layer_*.json"]),
        "cronistoria": pick_file(etl_dir, ["cronistoria_*.json"]),
        "correzioni": pick_file(etl_dir, ["correzioni_*.json"]),
    }

    catalogo = load_json(files["catalogo"])
    estrazione = load_json(files["estrazione"])

    correzioni = load_json(files["correzioni"])
    n_correzioni_attive = None
    if isinstance(correzioni, dict) and "correzioni" in correzioni:
        n_correzioni_attive = sum(
            1 for c in correzioni["correzioni"] if c.get("stato", "attiva") == "attiva"
        )

    result = {
        "etl_dir": etl_dir,
        "files": files,
        "n_correzioni_attive": n_correzioni_attive,
        "coverage": None,
    }

    if not catalogo or "clusters" not in catalogo:
        return result

    # tutti i documenti estratti (avanzamento + contenuto), qualunque sia lo schema
    docs_estratti = set()
    if estrazione and isinstance(estrazione, dict):
        for schema_key in ("avanzamento", "contenuto"):
            docs_estratti.update((estrazione.get(schema_key) or {}).keys())

    clusters = catalogo["clusters"]
    tot_doc_catalogo = sum(len(c.get("documents", [])) for c in clusters.values())

    cluster_coverage = []
    for cid, c in clusters.items():
        docs = c.get("documents", [])
        n_tot = len(docs)
        n_estratti = sum(1 for d in docs if d in docs_estratti)
        cluster_coverage.append({
            "cluster_id": cid,
            "label": c.get("label"),
            "tipo": c.get("tipo"),
            "n_documenti": n_tot,
            "n_estratti": n_estratti,
            "coperto": "completo" if n_estratti == n_tot and n_tot > 0
                       else ("parziale" if n_estratti > 0 else "non_coperto"),
        })

    cluster_coverage.sort(key=lambda x: (x["coperto"] != "completo", -x["n_documenti"]))

    result["coverage"] = {
        "n_cluster_totali": len(clusters),
        "n_documenti_totali_catalogo": tot_doc_catalogo,
        "n_documenti_estratti": len(docs_estratti),
        "cluster": cluster_coverage,
    }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", help="Cartella Progetti/ (o superiore) sotto cui cercare ETL_Documentale")
    ap.add_argument("--etl-dir", help="Path diretto a una cartella ETL_Documentale specifica")
    ap.add_argument("--project", help="Filtra solo le ETL_Documentale il cui path contiene questo nome progetto")
    args = ap.parse_args()

    if args.etl_dir:
        dirs = [args.etl_dir]
    elif args.root:
        dirs = find_etl_dirs(args.root)
        if args.project:
            dirs = [d for d in dirs if args.project.lower() in d.lower()]
    else:
        raise SystemExit("Specificare --root oppure --etl-dir")

    out = [analyze_etl_dir(d) for d in dirs]
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
