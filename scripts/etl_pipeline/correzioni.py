#!/usr/bin/env python3
"""
Gestisce il registro delle correzioni utente di una knowledge base ETL
documentale (file `correzioni_<Progetto>.json` in Output/ETL_Documentale).

Le correzioni sono ANNOTAZIONI: non modificano mai catalogo, estrazione,
knowledge layer o cronistoria. Vengono lette da `etl-kb-query` e citate
accanto alla fonte a cui si riferiscono. Una correzione non si cancella: si
marca come `superata` (cosi' resta la cronologia).

Uso:
    python3 correzioni.py add --etl-dir <ETL_Documentale> --tipo correzione \
        --documento "percorso/Doc.pptx" --testo "..." [--motivo "..."] [--autore "..."]
    python3 correzioni.py list --etl-dir <ETL_Documentale> [--tutte]
    python3 correzioni.py find --etl-dir <ETL_Documentale> --query "firma digitale"
    python3 correzioni.py supersede --etl-dir <ETL_Documentale> --id C003 [--sostituita-da C007]
    python3 correzioni.py forget --etl-dir <ETL_Documentale> --id C003   # eliminazione vera, su richiesta esplicita

Tipi: correzione | documento_non_affidabile | perimetro | nota
"""
import argparse
import glob
import json
import os
import sys
from datetime import date

TIPI = ("correzione", "documento_non_affidabile", "perimetro", "nota")


def find_file(etl_dir):
    matches = sorted(
        f for f in glob.glob(os.path.join(etl_dir, "correzioni_*.json"))
        if ".bak" not in os.path.basename(f)
    )
    return max(matches, key=os.path.getmtime) if matches else None


def default_path(etl_dir):
    # nome progetto = cartella due livelli sopra ETL_Documentale (Progetti/<Nome>/Output/...)
    nome = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(etl_dir))))
    return os.path.join(etl_dir, f"correzioni_{nome or 'progetto'}.json")


def load(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {"versione": 1}, "correzioni": []}


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def next_id(data):
    nums = [int(c["id"][1:]) for c in data["correzioni"] if c.get("id", "")[1:].isdigit()]
    return f"C{(max(nums) + 1 if nums else 1):03d}"


def cmd_add(a):
    path = find_file(a.etl_dir) or default_path(a.etl_dir)
    data = load(path)
    rif = {k: v for k, v in (("documento", a.documento), ("entita", a.entita), ("tema", a.tema)) if v}
    if not rif:
        sys.exit("Serve almeno uno tra --documento, --entita, --tema")
    voce = {
        "id": next_id(data),
        "tipo": a.tipo,
        "riferimento": rif,
        "testo": a.testo,
        "motivo": a.motivo,
        "autore": a.autore,
        "data": a.data or date.today().isoformat(),
        "stato": "attiva",
    }
    data["correzioni"].append(voce)
    save(path, data)
    print(json.dumps({"file": path, "aggiunta": voce}, indent=2, ensure_ascii=False))


def attive(data):
    return [c for c in data["correzioni"] if c.get("stato", "attiva") == "attiva"]


def cmd_list(a):
    path = find_file(a.etl_dir)
    data = load(path)
    voci = data["correzioni"] if a.tutte else attive(data)
    print(json.dumps({"file": path, "n": len(voci), "correzioni": voci}, indent=2, ensure_ascii=False))


def cmd_find(a):
    path = find_file(a.etl_dir)
    data = load(path)
    termini = [t.lower() for t in a.query.split() if t]
    out = []
    for c in attive(data):
        blob = json.dumps(c, ensure_ascii=False).lower()
        if any(t in blob for t in termini):
            out.append(c)
    print(json.dumps({"file": path, "n": len(out), "correzioni": out}, indent=2, ensure_ascii=False))


def cmd_supersede(a):
    path = find_file(a.etl_dir)
    data = load(path)
    for c in data["correzioni"]:
        if c["id"] == a.id:
            c["stato"] = "superata"
            c["superata_il"] = date.today().isoformat()
            if a.sostituita_da:
                c["sostituita_da"] = a.sostituita_da
            save(path, data)
            print(json.dumps(c, indent=2, ensure_ascii=False))
            return
    sys.exit(f"Correzione {a.id} non trovata")


def cmd_forget(a):
    path = find_file(a.etl_dir)
    data = load(path)
    n0 = len(data["correzioni"])
    data["correzioni"] = [c for c in data["correzioni"] if c["id"] != a.id]
    if len(data["correzioni"]) == n0:
        sys.exit(f"Correzione {a.id} non trovata")
    save(path, data)
    print(f"Eliminata {a.id}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--etl-dir", required=True)

    p = sub.add_parser("add"); common(p)
    p.add_argument("--tipo", choices=TIPI, default="correzione")
    p.add_argument("--documento"); p.add_argument("--entita"); p.add_argument("--tema")
    p.add_argument("--testo", required=True)
    p.add_argument("--motivo"); p.add_argument("--autore"); p.add_argument("--data")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list"); common(p)
    p.add_argument("--tutte", action="store_true", help="include anche le superate")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("find"); common(p)
    p.add_argument("--query", required=True)
    p.set_defaults(fn=cmd_find)

    p = sub.add_parser("supersede"); common(p)
    p.add_argument("--id", required=True); p.add_argument("--sostituita-da")
    p.set_defaults(fn=cmd_supersede)

    p = sub.add_parser("forget"); common(p)
    p.add_argument("--id", required=True)
    p.set_defaults(fn=cmd_forget)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
