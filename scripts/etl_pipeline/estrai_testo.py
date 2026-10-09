#!/usr/bin/env python3
"""
Estrazione testo grezzo per documenti (utility di supporto a Fase 3)
=======================================================================
Non è una fase della pipeline: è un'utility che dumpa il testo grezzo di
un elenco di documenti (stessi estrattori per formato già usati da
`catalogazione.py`: pptx, docx, xlsx, pdf, html, csv, md, txt, sql) in un
unico JSON {percorso_relativo: testo}. Serve per dare a chi/cosa fa
l'estrazione di Fase 3 (lettura + compilazione dello schema avanzamento/
contenuto) il testo già pronto, senza dover rileggere i file binari.

Uso:
    python3 estrai_testo.py --root "/percorso/Progetto DG" \
        --paths-file elenco_percorsi.txt --output testo_grezzo.json
"""
import argparse
import json
from pathlib import Path

from catalogazione import extract_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--paths-file", required=True, help="Un percorso relativo per riga")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    rel_paths = [l.strip() for l in Path(args.paths_file).read_text(encoding="utf-8").splitlines() if l.strip()]

    out = {}
    for rel in rel_paths:
        p = root / rel
        ext = p.suffix.lower().lstrip(".")
        if not p.exists():
            out[rel] = {"status": "mancante", "testo": None}
            continue
        text, status = extract_text(p, ext)
        out[rel] = {"status": status, "testo": text}

    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for v in out.values() if v["status"] == "estratto")
    print(f"Estratti correttamente: {ok}/{len(out)}. Scritto: {args.output}")


if __name__ == "__main__":
    main()
