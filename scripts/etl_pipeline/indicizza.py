#!/usr/bin/env python3
"""
Fase 1 - Indicizzazione
========================
Flusso ETL Documentale (Governance / Challenge 1 - Knowledge & Governance)

Cosa fa questo script:
- Scansiona una cartella (ricorsivamente) e trova tutti i documenti.
- Confronta ogni documento con l'indice esistente (index.json):
    - se il file non è nell'indice           -> lo indicizza come NUOVO
    - se il file è nell'indice ma è cambiato  -> lo aggiorna come AGGIORNATO
      (cambiato = hash del contenuto diverso da quello registrato)
    - se il file è nell'indice e non è cambiato -> INVARIATO (nessuna azione)
    - se un file registrato nell'indice non si trova più su disco -> MANCANTE
- Ogni documento ha un ID stabile e una cronistoria (history) di eventi,
  così le fasi successive del flusso (catalogazione, estrazione, knowledge
  layer) possono sempre risalire a quando/come è stato indicizzato.

Uso:
    python3 indicizza.py --root "/percorso/della/cartella" --index "/percorso/index.json"
    python3 indicizza.py --root "/percorso/della/cartella" --index "/percorso/index.json" --report report.md

Rilanciabile: ogni esecuzione successiva confronta lo stato attuale della
cartella con l'indice salvato e aggiorna solo ciò che è cambiato.
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# File di sistema/temporanei da ignorare sempre
IGNORE_NAMES = {".DS_Store", "Thumbs.db"}
IGNORE_PREFIXES = ("~$", ".~lock.")  # lock file di Office / LibreOffice


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def should_ignore(filename: str) -> bool:
    if filename in IGNORE_NAMES:
        return True
    if filename.startswith(IGNORE_PREFIXES):
        return True
    return False


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash sha256 del contenuto, letto a blocchi (per file grandi es. video)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def load_index(index_path: Path) -> dict:
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "documents": {}}


def save_index(index_path: Path, index: dict):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2, sort_keys=True)


def scan_folder(root: Path):
    """Ritorna { relpath_posix: Path assoluto } per tutti i file da considerare."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if should_ignore(name):
                continue
            abs_path = Path(dirpath) / name
            rel_path = abs_path.relative_to(root).as_posix()
            found[rel_path] = abs_path
    return found


def run(root: Path, index_path: Path):
    index = load_index(index_path)
    documents = index.setdefault("documents", {})

    on_disk = scan_folder(root)
    run_time = now_iso()

    counts = {"nuovo": 0, "aggiornato": 0, "invariato": 0, "mancante": 0, "non_leggibile": 0, "errore": 0}
    details = {"nuovo": [], "aggiornato": [], "mancante": [], "non_leggibile": [], "errore": []}

    seen_relpaths = set()

    for rel_path, abs_path in sorted(on_disk.items()):
        seen_relpaths.add(rel_path)
        try:
            st = abs_path.stat()
            size_bytes = st.st_size
            mtime_iso = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
        except OSError as e:
            counts["errore"] += 1
            details["errore"].append(f"{rel_path} ({e})")
            continue

        try:
            content_hash = hash_file(abs_path)
        except OSError as e:
            # Il file esiste (lo stat è riuscito) ma il contenuto non è leggibile
            # in questo momento: caso tipico dei file OneDrive/SharePoint
            # "solo online" non ancora sincronizzati localmente (0 blocchi su disco
            # nonostante una dimensione dichiarata > 0). Lo registriamo comunque
            # nell'indice come presente-ma-non-leggibile, senza scartarlo.
            entry = documents.get(rel_path)
            note = f"Contenuto non leggibile ({e}); probabile file cloud-only non sincronizzato localmente."
            if entry is None:
                entry = {
                    "id": str(uuid.uuid4()),
                    "filename": abs_path.name,
                    "extension": abs_path.suffix.lower().lstrip("."),
                    "size_bytes": size_bytes,
                    "content_hash": None,
                    "first_indexed_at": run_time,
                    "last_seen_at": run_time,
                    "last_modified_at": mtime_iso,
                    "status": "non_leggibile",
                    "note": note,
                    "history": [{"event": "trovato_non_leggibile", "timestamp": run_time, "note": note}],
                }
                documents[rel_path] = entry
            else:
                entry["last_seen_at"] = run_time
                entry["status"] = "non_leggibile"
                entry["note"] = note
                entry.setdefault("history", []).append(
                    {"event": "trovato_non_leggibile", "timestamp": run_time, "note": note}
                )
            counts["non_leggibile"] += 1
            details["non_leggibile"].append(rel_path)
            continue

        entry = documents.get(rel_path)

        if entry is None:
            # NUOVO documento: mai visto prima
            entry = {
                "id": str(uuid.uuid4()),
                "filename": abs_path.name,
                "extension": abs_path.suffix.lower().lstrip("."),
                "size_bytes": size_bytes,
                "content_hash": content_hash,
                "first_indexed_at": run_time,
                "last_seen_at": run_time,
                "last_modified_at": mtime_iso,
                "status": "indicizzato",
                "history": [
                    {"event": "indicizzato", "timestamp": run_time, "hash": content_hash}
                ],
            }
            documents[rel_path] = entry
            counts["nuovo"] += 1
            details["nuovo"].append(rel_path)

        elif entry.get("content_hash") != content_hash:
            # AGGIORNATO: file già noto ma contenuto cambiato
            entry["content_hash"] = content_hash
            entry["size_bytes"] = size_bytes
            entry["last_seen_at"] = run_time
            entry["last_modified_at"] = mtime_iso
            entry["status"] = "indicizzato"
            entry.pop("note", None)
            entry.setdefault("history", []).append(
                {"event": "aggiornato", "timestamp": run_time, "hash": content_hash}
            )
            counts["aggiornato"] += 1
            details["aggiornato"].append(rel_path)

        else:
            # INVARIATO: già indicizzato, nessuna modifica
            entry["last_seen_at"] = run_time
            if entry.get("status") in ("mancante", "non_leggibile"):
                # era segnato mancante/non leggibile ed è tornato disponibile
                entry["status"] = "indicizzato"
                entry.pop("note", None)
                entry.setdefault("history", []).append(
                    {"event": "ritrovato", "timestamp": run_time, "hash": content_hash}
                )
            counts["invariato"] += 1

    # File registrati nell'indice ma non più trovati su disco
    for rel_path, entry in documents.items():
        if rel_path not in seen_relpaths and entry.get("status") != "mancante":
            entry["status"] = "mancante"
            entry.setdefault("history", []).append(
                {"event": "non_trovato", "timestamp": run_time}
            )
            counts["mancante"] += 1
            details["mancante"].append(rel_path)

    index["meta"] = {
        "root": str(root),
        "last_run_at": run_time,
        "tool": "indicizza.py",
        "tool_version": "1.0",
        "totale_documenti_indice": len(documents),
    }

    save_index(index_path, index)
    return counts, details, len(documents)


def print_report(root, index_path, counts, details, totale):
    print(f"Cartella analizzata : {root}")
    print(f"Indice              : {index_path}")
    print("-" * 60)
    print(f"Nuovi documenti indicizzati : {counts['nuovo']}")
    print(f"Documenti aggiornati        : {counts['aggiornato']}")
    print(f"Documenti invariati          : {counts['invariato']}")
    print(f"Documenti mancanti           : {counts['mancante']}")
    print(f"Documenti non leggibili (cloud-only?) : {counts['non_leggibile']}")
    if counts["errore"]:
        print(f"Errori di lettura            : {counts['errore']}")
    print(f"Totale documenti nell'indice : {totale}")

    for label, key in [("NUOVI", "nuovo"), ("AGGIORNATI", "aggiornato"), ("MANCANTI", "mancante"), ("NON LEGGIBILI", "non_leggibile")]:
        if details[key]:
            print(f"\n{label}:")
            for item in details[key]:
                print(f"  - {item}")


def write_markdown_report(path: Path, root, counts, details, totale, run_time):
    lines = []
    lines.append(f"# Report indicizzazione — {run_time}")
    lines.append("")
    lines.append(f"Cartella: `{root}`")
    lines.append("")
    lines.append("| Esito | # |")
    lines.append("|---|---|")
    lines.append(f"| Nuovi | {counts['nuovo']} |")
    lines.append(f"| Aggiornati | {counts['aggiornato']} |")
    lines.append(f"| Invariati | {counts['invariato']} |")
    lines.append(f"| Mancanti | {counts['mancante']} |")
    lines.append(f"| Non leggibili (cloud-only?) | {counts['non_leggibile']} |")
    lines.append(f"| Totale nell'indice | {totale} |")
    lines.append("")
    for label, key in [("Nuovi", "nuovo"), ("Aggiornati", "aggiornato"), ("Mancanti", "mancante"), ("Non leggibili", "non_leggibile")]:
        if details[key]:
            lines.append(f"## {label}")
            for item in details[key]:
                lines.append(f"- {item}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Fase 1 - Indicizzazione documenti")
    parser.add_argument("--root", required=True, help="Cartella da indicizzare")
    parser.add_argument("--index", required=True, help="Percorso del file indice (JSON)")
    parser.add_argument("--report", help="Percorso opzionale per un report markdown della run")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index_path = Path(args.index).resolve()

    if not root.is_dir():
        print(f"Errore: la cartella '{root}' non esiste.", file=sys.stderr)
        sys.exit(1)

    counts, details, totale = run(root, index_path)
    print_report(root, index_path, counts, details, totale)

    if args.report:
        write_markdown_report(Path(args.report), root, counts, details, totale, now_iso())
        print(f"\nReport scritto in: {args.report}")


if __name__ == "__main__":
    main()
