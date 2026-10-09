#!/usr/bin/env python3
"""Aggiorna knowledge_layer_pilota_report.md: header, nuovo Esempio 4, rigenera le due liste complete."""
import json
from pathlib import Path

BASE = Path("/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale")
kl = json.load(open(BASE / "knowledge_layer_pilota.json", encoding="utf-8"))
text = (BASE / "knowledge_layer_pilota_report.md").read_text(encoding="utf-8")

n_persone = len(kl["persone"])
n_sistemi = len(kl["sistemi_tool"])
n_rif = len(kl["riferimenti_normativi"])

lines = text.split("\n")

# 1) header count line (riga 3, indice 2)
for i, l in enumerate(lines):
    if l.startswith("# Knowledge Layer"):
        lines[i] = "# Knowledge Layer — pilota (cluster 1+9 avanzamento, cluster 2+3+4+5+21 contenuto)"
    if l.startswith("Entità indicizzate:"):
        lines[i] = f"Entità indicizzate: {n_persone} persone, {n_sistemi} sistemi/tool (canonicalizzati), {n_rif} riferimenti normativi (raggruppati per famiglia, non fusi)."

text = "\n".join(lines)

# 2) inserisce Esempio 4 prima di "## Riferimenti normativi"
peter = next(p for p in kl["persone"] if p["id"] == "peter-durante")
esempio4 = []
esempio4.append('## Esempio 4 — Estensione 4 agosto 2026: rete di ruoli da circolari organizzative ripetute ("Peter Durante")')
esempio4.append("")
esempio4.append(
    "Con l'estensione ai cluster 3, 4, 5, 9 sono state processate 8 circolari organizzative ITH CO (13-25 "
    "..20-25) oltre alla ITH CO 06-25 già in KB. Ogni circolare cita 'Peter Durante' come Chief People, "
    "Innovation & Transformation Officer: il Knowledge Layer accumula così 8 menzioni per la stessa persona "
    "invece di trattarle come 8 entità diverse — un esempio concreto di deduplicazione che rende visibile un "
    "pattern (la stessa figura è responsabile People/HR trasversale a tutte le funzioni)."
)
esempio4.append("")
for m in peter["menzioni"]:
    esempio4.append(f"- **{m['documento']}** ({m['data']}, {m['tipo_documento']}) — {m['contesto']}")
esempio4.append("")
esempio4.append(
    "Vedi `cronistoria_pilota.json` → `avvisi_qualita_dati` per i casi di identificazione incerta emersi in "
    "questa estensione (es. 'Aprea' → 'Domenico Aprea' per inferenza cross-documento; 'Nunziangelo Ferrulli' "
    "trattato come variante di 'Nunzio Ferrulli')."
)
esempio4.append("")

marker = "## Riferimenti normativi"
idx = text.index(marker)
text = text[:idx] + "\n".join(esempio4) + "\n" + text[idx:]

# 3) rigenera le due sezioni finali (elenchi completi)
head, _, _ = text.partition("## Persone indicizzate")
lines_out = [head.rstrip("\n"), ""]
lines_out.append("## Persone indicizzate (elenco completo)")
lines_out.append("")
for p in sorted(kl["persone"], key=lambda x: x["nome_canonico"]):
    alias = f" [alias: {', '.join(p['alias'])}]" if p["alias"] else ""
    lines_out.append(f"- {p['nome_canonico']}{alias} ({len(p['menzioni'])} menzioni)")
lines_out.append("")
lines_out.append("## Sistemi/tool indicizzati (canonicalizzati)")
lines_out.append("")
for s in sorted(kl["sistemi_tool"], key=lambda x: x["nome_canonico"]):
    alias = f" [alias: {', '.join(s['alias'])}]" if s["alias"] else ""
    lines_out.append(f"- {s['nome_canonico']}{alias} ({len(s['menzioni'])} menzioni)")
lines_out.append("")

Path(BASE / "knowledge_layer_pilota_report.md").write_text("\n".join(lines_out), encoding="utf-8")
print("OK — persone:", n_persone, "sistemi_tool:", n_sistemi, "riferimenti_normativi:", n_rif)
