#!/usr/bin/env python3
"""
Verifica automatica dei profili di Estrazione contro il testo sorgente (controllo anti-invenzione).

Per ogni documento con `profilo`, controlla che nomi di oggetti, di campi e di KPI compaiano nel
testo letto (confronto normalizzato: maiuscole, spazi, Unicode NFC). Non verifica formule né
descrizioni: misura solo quanto i nomi sono ancorati al testo.

Uso:
    python3 verifica_profili.py --estrazione estrazione_X.json --batch-dir "<cartella con batch_N.json>" [--soglia 0.85]
I batch sono i file {percorso: {testo: ...}} passati ai subagent di Estrazione.
Segnala i documenti con almeno 8 campi e copertura sotto soglia.
"""
import argparse
import glob
import json
import re
import unicodedata


def nf(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(s))).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estrazione", required=True)
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--soglia", type=float, default=0.85)
    a = ap.parse_args()
    src = {}
    for f in glob.glob(a.batch_dir.rstrip("/") + "/batch_*.json"):
        for d, v in json.load(open(f, encoding="utf-8")).items():
            src[nf(d)] = nf(v["testo"])
    est = json.load(open(a.estrazione, encoding="utf-8"))
    campi = campi_ok = ogg = ogg_ok = kpi = kpi_ok = 0
    bassi = []
    for sec in ("avanzamento", "contenuto"):
        for doc, r in est.get(sec, {}).items():
            p = r.get("profilo")
            if not p:
                continue
            t = src.get(nf(doc), "")
            dc = dh = 0
            for o in p.get("oggetti_dati", []):
                ogg += 1
                ogg_ok += nf(o.get("nome", "")) in t
                for c in o.get("campi", []):
                    dc += 1
                    dh += nf(c.get("nome", "")) in t
            for rp in p.get("report", []):
                for k in rp.get("kpi", []):
                    kpi += 1
                    kpi_ok += nf(k.get("nome", "")) in t
            campi += dc
            campi_ok += dh
            if dc >= 8 and dh / dc < a.soglia:
                bassi.append((doc, dc, dh))
    pc = lambda x, y: (100 * x / y) if y else 0
    print(f"campi ancorati al testo: {campi_ok}/{campi} ({pc(campi_ok, campi):.1f}%)")
    print(f"oggetti: {ogg_ok}/{ogg} ({pc(ogg_ok, ogg):.1f}%) | nomi KPI: {kpi_ok}/{kpi} ({pc(kpi_ok, kpi):.1f}%)")
    for d, dc, dh in bassi:
        print(f"  sotto soglia: {d} ({dh}/{dc})")


if __name__ == "__main__":
    main()
