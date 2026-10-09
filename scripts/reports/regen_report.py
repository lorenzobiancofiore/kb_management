import json, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    data = json.load(f)

lines = []
lines.append("# Pilota Estrazione — Fase 3 (cluster 1 = avanzamento, cluster 2 = contenuto)")
lines.append("")
lines.append(f"Cluster 1 (avanzamento): {len(data['avanzamento'])} documenti — Cluster 2 (contenuto): {len(data['contenuto'])} documenti")
lines.append("")
lines.append("Nota sulle date: per i documenti di avanzamento, `data_documento` è quasi sempre stata dedotta dalla data di modifica del file (fonte 'data_modifica_file'), non dal contenuto — vedi campo `Fonte data`. È un'approssimazione: attendibile per l'ordinamento generale, ma da NON considerare come data certa dell'evento (es. una riunione slittata non cambia il file, un file ritoccato dopo non cambia la riunione a cui si riferisce).")
lines.append("")
lines.append("## Cluster 1 — Avanzamento")
lines.append("")

av_items = sorted(data["avanzamento"].items(), key=lambda kv: (kv[1].get("data_documento") or "9999"))
for path, r in av_items:
    lines.append(f"### {path}")
    lines.append("")
    lines.append(f"- **Data documento**: {r.get('data_documento')}")
    lines.append(f"- **Fonte data**: {r.get('data_fonte')}")
    lines.append(f"- **Partecipanti**: {', '.join(r.get('partecipanti') or []) or '—'}")
    lines.append(f"- **Contenuti trattati**: {'; '.join(r.get('contenuti_trattati') or []) or '—'}")
    lines.append(f"- **Decisioni**: {'; '.join(r.get('decisioni') or []) or '—'}")
    ai = r.get("action_item") or []
    if ai:
        lines.append("- **Action item**:")
        for a in ai:
            lines.append(f"  - {a.get('descrizione')} (resp: {a.get('responsabile') or '—'}, scadenza: {a.get('scadenza') or '—'})")
    else:
        lines.append("- **Action item**: —")
    lines.append(f"- **Rischi/blocchi**: {'; '.join(r.get('rischi_blocchi') or []) or '—'}")
    lines.append(f"- **Prossimi passi**: {'; '.join(r.get('prossimi_passi') or []) or '—'}")
    lines.append("")

lines.append("## Cluster 2 — Contenuto")
lines.append("")

cont_items = sorted(data["contenuto"].items(), key=lambda kv: kv[0])
for path, r in cont_items:
    lines.append(f"### {path}")
    lines.append("")
    lines.append(f"- **Sotto-tipo**: {r.get('sotto_tipo')}")
    lines.append(f"- **Argomento**: {r.get('argomento')}")
    lines.append(f"- **Processi/attività**: {'; '.join(r.get('processi_attivita') or []) or '—'}")
    lines.append(f"- **Ruoli/responsabilità**: {'; '.join(r.get('ruoli_responsabilita') or []) or '—'}")
    lines.append(f"- **Sistemi/tool citati**: {', '.join(r.get('sistemi_tool_citati') or []) or '—'}")
    lines.append(f"- **Riferimenti normativi**: {'; '.join(r.get('riferimenti_normativi') or []) or '—'}")
    fonte = r.get("versione_data_fonte")
    fonte_str = f" (fonte: {fonte})" if fonte else ""
    lines.append(f"- **Versione/data validità**: {r.get('versione_data_validita')}{fonte_str}")
    lines.append("")

with open(os.path.join(BASE, "estrazione_pilota_report.md"), "w") as f:
    f.write("\n".join(lines))

print("Report rigenerato.")
