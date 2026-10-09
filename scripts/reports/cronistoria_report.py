import json, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "cronistoria_pilota.json")) as f:
    cron = json.load(f)

lines = []
lines.append("# Cronistoria — pilota (cluster 1, avanzamento)")
lines.append("")
lines.append("Due parti: (1) la timeline meccanica delle decisioni ordinate per data — nessuna interpretazione, solo ordinamento; (2) i casi in cui una decisione successiva sembra aggiornare/sostituire una precedente — **queste sono ipotesi generate leggendo il testo, da validare con chi ha vissuto i meeting, non fatti verificati**.")
lines.append("")

lines.append("## Timeline decisioni — cluster 1 (avanzamento)")
lines.append("")
for item in cron["timeline_decisioni_cluster1"]:
    lines.append(f"### {item['data']} — {item['documento']}")
    lines.append(f"*(fonte data: {item['fonte_data']})*")
    lines.append("")
    if item["decisioni"]:
        for d in item["decisioni"]:
            lines.append(f"- {d}")
    else:
        lines.append("- (nessuna decisione estratta)")
    lines.append("")

lines.append("## Possibili aggiornamenti/sostituzioni tra decisioni (da validare)")
lines.append("")
for pa in cron["possibili_aggiornamenti_decisioni"]:
    lines.append(f"### {pa['tema']} — confidenza: {pa['confidenza']}")
    lines.append("")
    lines.append(f"**Decisione precedente** ({pa['decisione_precedente']['data']}, *{pa['decisione_precedente']['documento']}*): {pa['decisione_precedente']['testo']}")
    lines.append("")
    lines.append(f"**Decisione successiva** ({pa['decisione_successiva']['data']}, *{pa['decisione_successiva']['documento']}*): {pa['decisione_successiva']['testo']}")
    if "eseguita_in" in pa:
        e = pa["eseguita_in"]
        lines.append("")
        lines.append(f"**Eseguita in** ({e['data']}, *{e['documento']}*): {e['testo']}")
    lines.append("")
    lines.append(f"*Nota: {pa['nota']}*")
    lines.append("")

lines.append("## Avvisi qualità dati")
lines.append("")
for a in cron["avvisi_qualita_dati"]:
    lines.append(f"- {a['descrizione']}")
lines.append("")

with open(os.path.join(BASE, "cronistoria_pilota_report.md"), "w") as f:
    f.write("\n".join(lines))
print("Report cronistoria generato.")
