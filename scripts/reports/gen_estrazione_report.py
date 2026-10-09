#!/usr/bin/env python3
"""Rigenera estrazione_pilota_report.md dal JSON, stesso formato usato finora."""
import json
from pathlib import Path

BASE = Path("/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale")
est = json.load(open(BASE / "estrazione_pilota_cluster1_2.json", encoding="utf-8"))

def j(lst):
    return "; ".join(lst) if lst else "—"

lines = []
n_av = len(est["avanzamento"])
n_co = len(est["contenuto"])
lines.append(f"# Pilota Estrazione — Fase 3 (cluster 1+9 = avanzamento, cluster 2+3+4+5+21 = contenuto)")
lines.append("")
lines.append(f"Avanzamento: {n_av} documenti — Contenuto: {n_co} documenti")
lines.append("")
lines.append(
    "Nota sulle date: per i documenti di avanzamento, `data_documento` è quasi sempre stata dedotta dalla "
    "data di modifica del file (fonte 'data_modifica_file'), non dal contenuto — vedi campo `Fonte data`. "
    "È un'approssimazione: attendibile per l'ordinamento generale, ma da NON considerare come data certa "
    "dell'evento (es. una riunione slittata non cambia il file, un file ritoccato dopo non cambia la "
    "riunione a cui si riferisce)."
)
lines.append("")
lines.append(
    "Perimetro esteso il 4 agosto 2026 con i cluster 3 (Reclami), 4 (formazione), 5 (circolari "
    "organizzative/workspace) e 9 (SAL/piano Bludigit) — vedi `README.md` e `cronistoria_pilota.json` "
    "(`avvisi_qualita_dati`) per le note di qualità dati emerse con l'estensione."
)
lines.append("")
lines.append("## Avanzamento")
lines.append("")

for doc, rec in est["avanzamento"].items():
    lines.append(f"### {doc}")
    lines.append("")
    lines.append(f"- **Data documento**: {rec.get('data_documento') or '—'}")
    lines.append(f"- **Fonte data**: {rec.get('data_fonte') or '—'}")
    lines.append(f"- **Partecipanti**: {j(rec.get('partecipanti'))}")
    lines.append(f"- **Contenuti trattati**: {j(rec.get('contenuti_trattati'))}")
    lines.append(f"- **Decisioni**: {j(rec.get('decisioni'))}")
    ai = rec.get("action_item") or []
    if ai:
        lines.append("- **Action item**:")
        for a in ai:
            lines.append(f"  - {a.get('descrizione')} (resp: {a.get('responsabile') or '—'}, scadenza: {a.get('scadenza') or '—'})")
    else:
        lines.append("- **Action item**: —")
    lines.append(f"- **Rischi/blocchi**: {j(rec.get('rischi_blocchi'))}")
    lines.append(f"- **Prossimi passi**: {j(rec.get('prossimi_passi'))}")
    lines.append("")

lines.append("## Contenuto")
lines.append("")

for doc, rec in est["contenuto"].items():
    lines.append(f"### {doc}")
    lines.append("")
    lines.append(f"- **Sotto-tipo**: {rec.get('sotto_tipo') or '—'}")
    lines.append(f"- **Argomento**: {rec.get('argomento') or '—'}")
    lines.append(f"- **Processi/attività**: {j(rec.get('processi_attivita'))}")
    lines.append(f"- **Ruoli/responsabilità**: {j(rec.get('ruoli_responsabilita'))}")
    lines.append(f"- **Sistemi/tool citati**: {j(rec.get('sistemi_tool_citati'))}")
    lines.append(f"- **Riferimenti normativi**: {j(rec.get('riferimenti_normativi'))}")
    lines.append(f"- **Versione/data validità**: {rec.get('versione_data_validita') or '—'}")
    lines.append("")

Path(BASE / "estrazione_pilota_report.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Scritto estrazione_pilota_report.md — avanzamento {n_av}, contenuto {n_co}")
