import json, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "knowledge_layer_pilota.json")) as f:
    kl = json.load(f)
with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    est = json.load(f)

lines = []
lines.append("# Knowledge Layer — pilota (cluster 1 avanzamento + cluster 2 contenuto)")
lines.append("")
lines.append(f"Entità indicizzate: {len(kl['persone'])} persone, {len(kl['sistemi_tool'])} sistemi/tool (canonicalizzati), {len(kl['riferimenti_normativi'])} riferimenti normativi (raggruppati per famiglia, non fusi).")
lines.append("")
lines.append("## Cosa fa questo livello")
lines.append("")
lines.append("Prende l'estrazione documento-per-documento di Fase 3 e la riorganizza per entità: ogni persona, sistema/tool o riferimento normativo porta con sé la lista dei documenti che la citano, con data e fonte della data. Permette due tipi di domande: puntuali (\"cosa sappiamo su X\") e di sintesi su più documenti (\"come si è evoluto un tema nel tempo\"). Sotto due esempi concreti.")
lines.append("")

lines.append("## Esempio 1 — Query puntuale: \"Databricks\"")
lines.append("")
databricks = next(s for s in kl["sistemi_tool"] if s["nome_canonico"] == "Databricks")
lines.append(f"Alias raccolti nei documenti originali: {', '.join(databricks['alias']) if databricks['alias'] else '—'}")
lines.append("")
lines.append("Citato in:")
for m in databricks["menzioni"]:
    lines.append(f"- **{m['documento']}** ({m['data']}, fonte data: {m['fonte_data']}) — \"{m['contesto']}\"")
lines.append("")

lines.append("## Esempio 2 — Sintesi multi-documento: evoluzione della persona \"Alessio Lippi\"")
lines.append("")
lines.append("Alessio Lippi compare sia come partecipante/responsabile in documenti di avanzamento sia come referente in documenti di contenuto — un esempio di come il Knowledge Layer collega la stessa persona attraverso categorie diverse di documento.")
lines.append("")
lippi = next(p for p in kl["persone"] if p["nome_canonico"] == "Alessio Lippi")
for m in lippi["menzioni"]:
    lines.append(f"- **{m['documento']}** ({m['data']}, {m['tipo_documento']}) — {m['contesto']}")
lines.append("")

lines.append("## Esempio 3 — Query puntuale su persona con più menzioni: \"Lorenzo Biancofiore\"")
lines.append("")
lb = next(p for p in kl["persone"] if p["nome_canonico"] == "Lorenzo Biancofiore")
for m in lb["menzioni"]:
    lines.append(f"- **{m['documento']}** ({m['data']}, {m['tipo_documento']}) — {m['contesto']}")
lines.append("")

lines.append("## Riferimenti normativi — raggruppati per famiglia (non fusi)")
lines.append("")
lines.append("Qui NON ho unificato le voci simili in una sola entità: es. le diverse menzioni ARERA sembrano riferirsi a obblighi diversi (delibere, tracciati, dichiarazioni), non alla stessa norma citata con parole diverse. Le ho solo raggruppate per famiglia come prima categorizzazione — la normalizzazione fine (se due voci sono davvero la stessa norma) richiede giudizio di merito, non l'ho decisa io.")
lines.append("")
fam = {}
for n in kl["riferimenti_normativi"]:
    fam.setdefault(n["famiglia"], []).append(n)
for f_name, items in fam.items():
    lines.append(f"### {f_name} ({len(items)} voci)")
    for it in items:
        docs = ", ".join(sorted(set(m["documento"] for m in it["menzioni"])))
        lines.append(f"- {it['nome_canonico']} — *{docs}*")
    lines.append("")

lines.append("## Persone indicizzate (elenco completo)")
lines.append("")
for p in kl["persone"]:
    lines.append(f"- {p['nome_canonico']} ({len(p['menzioni'])} menzioni)")
lines.append("")

lines.append("## Sistemi/tool indicizzati (canonicalizzati)")
lines.append("")
for s in kl["sistemi_tool"]:
    alias_str = f" [alias: {', '.join(s['alias'])}]" if s["alias"] else ""
    lines.append(f"- {s['nome_canonico']}{alias_str} ({len(s['menzioni'])} menzioni)")
lines.append("")

with open(os.path.join(BASE, "knowledge_layer_pilota_report.md"), "w") as f:
    f.write("\n".join(lines))

print("Report generato.")
