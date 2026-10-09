#!/usr/bin/env python3
"""Aggiorna cronistoria_pilota_report.md: header, rigenera Timeline (meccanica),
estende 'Possibili aggiornamenti' e 'Avvisi qualità dati' (curate, solo append)."""
import json
from pathlib import Path

BASE = Path("/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale")
cr = json.load(open(BASE / "cronistoria_pilota.json", encoding="utf-8"))
text = (BASE / "cronistoria_pilota_report.md").read_text(encoding="utf-8")

# --- split file into the 3 known sections using markers ---
m_timeline = "## Timeline decisioni — cluster 1 (avanzamento)"
m_aggiorn = "## Possibili aggiornamenti/sostituzioni tra decisioni (da validare)"
m_avvisi = "## Avvisi qualità dati"

i_timeline = text.index(m_timeline)
i_aggiorn = text.index(m_aggiorn)
i_avvisi = text.index(m_avvisi)

header_intro = text[:i_timeline].rstrip("\n")
aggiorn_block = text[i_aggiorn:i_avvisi].rstrip("\n")
avvisi_block = text[i_avvisi:].rstrip("\n")

# 1) header update
lines = header_intro.split("\n")
for i, l in enumerate(lines):
    if l.startswith("# Cronistoria"):
        lines[i] = "# Cronistoria — pilota (cluster 1+9, avanzamento)"
header_intro = "\n".join(lines)

# 2) rigenera Timeline (meccanica, dal JSON) ------------------------------
timeline_lines = [m_timeline, ""]
for e in cr["timeline_decisioni_cluster1"]:
    timeline_lines.append(f"### {e['data']} — {e['documento']}")
    timeline_lines.append(f"*(fonte data: {e['fonte_data']})*")
    timeline_lines.append("")
    dec = e.get("decisioni") or []
    if dec:
        for d in dec:
            timeline_lines.append(f"- {d}")
    else:
        timeline_lines.append("- (nessuna decisione estratta)")
    timeline_lines.append("")
timeline_block = "\n".join(timeline_lines).rstrip("\n")

# 3) estendi 'Possibili aggiornamenti' con il nuovo tema -------------------
nuovo_tema = cr["possibili_aggiornamenti_decisioni"][-1]
assert nuovo_tema["tema"] == "Data di avvio del Pilota Reclami"

tema_lines = []
tema_lines.append(f"### {nuovo_tema['tema']} — confidenza: media (ripianificato più volte)")
tema_lines.append("")
for step in nuovo_tema["evoluzione"]:
    tema_lines.append(f"**{step['data']}** (*{step['documento']}*): {step['stato']}")
    tema_lines.append("")
tema_lines.append(f"*Nota: {nuovo_tema['nota']}*")

aggiorn_block = aggiorn_block + "\n\n" + "\n".join(tema_lines)

# 4) estendi 'Avvisi qualità dati' con i 6 nuovi avvisi --------------------
nuovi_avvisi = cr["avvisi_qualita_dati"][-6:]
avvisi_lines = []
for a in nuovi_avvisi:
    avvisi_lines.append(f"- **[{a['tipo']}]** {a['descrizione']}")
avvisi_block = avvisi_block + "\n" + "\n".join(avvisi_lines)

# --- ricompone il file ---
final = "\n\n".join([header_intro, timeline_block, aggiorn_block, avvisi_block]) + "\n"
Path(BASE / "cronistoria_pilota_report.md").write_text(final, encoding="utf-8")
print("OK — timeline:", len(cr["timeline_decisioni_cluster1"]),
      "| possibili_aggiornamenti:", len(cr["possibili_aggiornamenti_decisioni"]),
      "| avvisi:", len(cr["avvisi_qualita_dati"]))
