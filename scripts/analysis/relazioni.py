#!/usr/bin/env python3
"""
Relazioni tra entità (prototipo) — passo derivato, dopo Fase 3 ed Fase 4
=========================================================================
Flusso ETL Documentale (Governance / Challenge 1 - Knowledge & Governance)

Cosa fa questo script:
- Non è una nuova fase della pipeline a 5 fasi (Indicizzazione,
  Catalogazione, Estrazione, Knowledge Layer, Cronistoria): è un passo
  DERIVATO, prototipale, che gira dopo Estrazione (Fase 3) e Knowledge
  Layer (Fase 4) e ne combina gli output per proporre connessioni tra le
  entità canoniche già risolte dal Knowledge Layer. Non introduce nuova
  estrazione né nuovi tipi di entità: usa solo campi già presenti.
- Perimetro: stesso pilota di Estrazione/Knowledge Layer, cluster 1
  (avanzamento) + cluster 2 (contenuto) + cluster 21 (contenuto,
  completamento), esteso il 4 agosto 2026 con cluster 3 (contenuto,
  Reclami), cluster 4 (contenuto, formazione), cluster 5 (contenuto,
  circolari organizzative/workspace) e cluster 9 (avanzamento, SAL/piano
  Bludigit). Input: knowledge_layer_pilota.json,
  estrazione_pilota_cluster1_2.json.

Due livelli di relazione, entrambi deterministici e tracciabili al testo
sorgente (nessuna inferenza semantica):

- Livello A — co-occorrenza documentale
  Due entità canoniche (persona / sistema_tool / riferimento_normativo)
  che compaiono nelle "menzioni" dello stesso documento nel Knowledge
  Layer vengono collegate con un arco "co-menzionato-in". Costruito
  puramente dai dati già risolti dal Knowledge Layer, senza rileggere i
  documenti. Nessuna implicazione di relazione causale o organizzativa:
  è un segnale debole di prossimità.

- Livello B — relazione dichiarata esplicitamente nel testo
  - B1 "ruolo_dichiarato": per ogni persona la cui menzione ha un
    "contesto" che inizia con il prefisso "citato in ruoli/responsabilità:"
    (prodotto dal Knowledge Layer a partire dal campo Estrazione
    ruoli_responsabilita), viene creato un arco persona -> testo libero
    con il testo del ruolo/responsabilità così come scritto nel documento
    di origine.
  - B2 "responsabile_azione": per ogni action_item con responsabile non
    nullo nei documenti "avanzamento" di Estrazione, viene creato un arco
    ruolo_generico -> azione. ATTENZIONE: il campo "responsabile" in
    Estrazione contiene etichette di ruolo generiche (es. "Data Owner e
    Data Steward", "Data Governance team"), NON persone nominative. Questo
    livello NON collega quindi persone canoniche del Knowledge Layer ad
    azioni: collega un ruolo generico (testo libero) a un'azione (testo
    libero). Le persone nominative responsabili di ambiti/domini sono già
    intercettate da B1, quando il documento le esprime con quella
    formulazione.

Deliberatamente escluso: un ipotetico "Livello C" di relazioni inferite
semanticamente (non dichiarate esplicitamente nel testo) — troppo
rischioso per questo prototipo, che vuole restare interamente tracciabile
al testo sorgente citato in "evidenza_testuale".

Versioning: nessuna deduplicazione/cancellazione di archi più vecchi in
caso di conflitto — vale la stessa regola già in uso in Cronistoria
("documento più recente vince" per la LETTURA, non per la SCRITTURA):
tutti gli archi restano nell'output con la loro data/documento di
provenienza, e sarà chi legge (o un passo successivo) a decidere quale
versione considerare corrente in caso di contraddizione.

Uso:
    python3 relazioni.py \
        --knowledge-layer knowledge_layer_pilota.json \
        --estrazione estrazione_pilota_cluster1_2.json \
        --output relazioni_pilota.json \
        --report relazioni_pilota_report.md
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

RUOLI_PREFIX = "citato in ruoli/responsabilità:"


# ---------------------------------------------------------------------------
# Livello A — co-occorrenza documentale
# ---------------------------------------------------------------------------

def build_livello_a(kl):
    """Per ogni documento, raccoglie le entità canoniche che vi compaiono
    (via menzioni), poi genera un arco co-menzionato-in per ogni coppia di
    entità distinte che condividono almeno un documento. Gli archi tra la
    stessa coppia su documenti diversi vengono aggregati in un unico arco
    con peso = numero di documenti condivisi e la lista di quei documenti.
    """
    doc_to_entities = defaultdict(list)  # documento -> [(entity_id, tipo, nome)]

    for tipo_lista in ("persone", "sistemi_tool", "riferimenti_normativi"):
        for entita in kl.get(tipo_lista, []):
            eid = entita["id"]
            tipo = entita["tipo"]
            nome = entita["nome_canonico"]
            for m in entita.get("menzioni", []):
                doc = m.get("documento")
                if doc:
                    doc_to_entities[doc].append({
                        "id": eid,
                        "tipo": tipo,
                        "nome_canonico": nome,
                        "tipo_documento": m.get("tipo_documento"),
                        "data": m.get("data"),
                        "fonte_data": m.get("fonte_data"),
                    })

    pair_docs = defaultdict(list)  # (id1, id2) ordinata alfabeticamente -> [documento,...]
    pair_meta = {}

    for doc, entities in doc_to_entities.items():
        # dedup entità nello stesso documento (un'entità può avere più menzioni nello stesso doc)
        seen = {}
        for e in entities:
            seen[e["id"]] = e
        ids = sorted(seen.keys())
        for id1, id2 in combinations(ids, 2):
            key = (id1, id2)
            pair_docs[key].append({
                "documento": doc,
                "tipo_documento": seen[id1].get("tipo_documento"),
                "data": seen[id1].get("data"),
            })
            pair_meta[id1] = seen[id1]
            pair_meta[id2] = seen[id2]

    archi = []
    for (id1, id2), docs in sorted(pair_docs.items()):
        e1, e2 = pair_meta[id1], pair_meta[id2]
        archi.append({
            "livello": "A",
            "tipo_relazione": "co-menzionato-in",
            "da": {"id": id1, "tipo": e1["tipo"], "nome_canonico": e1["nome_canonico"]},
            "a": {"id": id2, "tipo": e2["tipo"], "nome_canonico": e2["nome_canonico"]},
            "peso": len(docs),
            "documenti": docs,
        })
    return archi


# ---------------------------------------------------------------------------
# Livello B1 — ruolo_dichiarato (persona -> testo libero, da Knowledge Layer)
# ---------------------------------------------------------------------------

def build_livello_b1(kl):
    archi = []
    for entita in kl.get("persone", []):
        eid = entita["id"]
        nome = entita["nome_canonico"]
        for m in entita.get("menzioni", []):
            contesto = (m.get("contesto") or "").strip()
            if contesto.lower().startswith(RUOLI_PREFIX.lower()):
                testo = contesto[len(RUOLI_PREFIX):].strip()
                if not testo:
                    continue
                archi.append({
                    "livello": "B",
                    "tipo_relazione": "ruolo_dichiarato",
                    "da": {"id": eid, "tipo": "persona", "nome_canonico": nome},
                    "a": {"tipo": "testo_libero", "valore": testo},
                    "documento": m.get("documento"),
                    "tipo_documento": m.get("tipo_documento"),
                    "data": m.get("data"),
                    "fonte_data": m.get("fonte_data"),
                    "evidenza_testuale": contesto,
                })
    return archi


# ---------------------------------------------------------------------------
# Livello B2 — responsabile_azione (ruolo_generico -> azione, da Estrazione)
# ---------------------------------------------------------------------------

def build_livello_b2(estrazione):
    archi = []
    for doc, record in estrazione.get("avanzamento", {}).items():
        data_doc = record.get("data_documento")
        for item in record.get("action_item", []) or []:
            responsabile = item.get("responsabile")
            descrizione = item.get("descrizione")
            if not responsabile or not descrizione:
                continue
            archi.append({
                "livello": "B",
                "tipo_relazione": "responsabile_azione",
                "da": {
                    "tipo": "ruolo_generico",
                    "valore": responsabile,
                    "nota": (
                        "Etichetta di ruolo generica come scritta nel documento "
                        "di origine (campo action_item.responsabile di Estrazione), "
                        "NON una persona nominativa del Knowledge Layer."
                    ),
                },
                "a": {"tipo": "azione", "valore": descrizione},
                "documento": doc,
                "tipo_documento": "avanzamento",
                "data": data_doc,
                "scadenza": item.get("scadenza"),
                "evidenza_testuale": f"responsabile: {responsabile} — azione: {descrizione}",
            })
    return archi


# ---------------------------------------------------------------------------
# Report leggibile
# ---------------------------------------------------------------------------

def build_report(archi_a, archi_b1, archi_b2, kl_path, est_path):
    lines = []
    lines.append("# Report relazioni tra entità (prototipo)")
    lines.append("")
    lines.append(
        "Passo derivato, non parte delle 5 fasi della pipeline. Gira dopo "
        "Estrazione e Knowledge Layer e ne combina gli output senza nuova "
        "estrazione. Perimetro: stesso pilota (cluster 1, 2, 3, 4, 5, 9, 21)."
    )
    lines.append("")
    lines.append(f"- Knowledge Layer di origine: `{kl_path}`")
    lines.append(f"- Estrazione di origine: `{est_path}`")
    lines.append("")
    lines.append("## Sintesi")
    lines.append("")
    lines.append("| Livello | Tipo relazione | # archi |")
    lines.append("|---|---|---|")
    lines.append(f"| A | co-menzionato-in | {len(archi_a)} |")
    lines.append(f"| B1 | ruolo_dichiarato | {len(archi_b1)} |")
    lines.append(f"| B2 | responsabile_azione | {len(archi_b2)} |")
    lines.append("")

    lines.append("## Livello A — co-occorrenza documentale (esempi)")
    lines.append("")
    lines.append(
        "Segnale debole di prossimità: nessuna implicazione causale o "
        "organizzativa, solo condivisione di almeno un documento."
    )
    lines.append("")
    top_a = sorted(archi_a, key=lambda a: -a["peso"])[:10]
    for a in top_a:
        lines.append(
            f"- **{a['da']['nome_canonico']}** ({a['da']['tipo']}) "
            f"↔ **{a['a']['nome_canonico']}** ({a['a']['tipo']}) "
            f"— peso {a['peso']} (documenti: "
            + ", ".join(d["documento"] for d in a["documenti"][:3])
            + (", ..." if len(a["documenti"]) > 3 else "")
            + ")"
        )
    lines.append("")

    lines.append("## Livello B1 — ruolo_dichiarato (esempi)")
    lines.append("")
    for b in archi_b1[:10]:
        lines.append(
            f"- **{b['da']['nome_canonico']}** → \"{b['a']['valore']}\" "
            f"(documento: `{b['documento']}`, data: {b['data']})"
        )
    lines.append("")

    lines.append("## Livello B2 — responsabile_azione (esempi)")
    lines.append("")
    lines.append(
        "**Nota importante**: `responsabile` qui è un'etichetta di ruolo "
        "generica come scritta nel documento (es. \"Data Owner e Data "
        "Steward\", \"Data Governance team\"), NON una persona nominativa "
        "del Knowledge Layer. Nei documenti del pilota, nessun "
        "`action_item.responsabile` nomina una persona specifica."
    )
    lines.append("")
    for b in archi_b2[:10]:
        lines.append(
            f"- **{b['da']['valore']}** → \"{b['a']['valore']}\" "
            f"(documento: `{b['documento']}`, data: {b['data']})"
        )
    lines.append("")

    lines.append("## Cosa NON fa questo prototipo")
    lines.append("")
    lines.append(
        "- Non inferisce relazioni non dichiarate esplicitamente nel testo "
        "(nessun \"Livello C\" semantico)."
    )
    lines.append(
        "- Non introduce un'entità canonica \"dominio\" — i domini citati "
        "in `ruolo_dichiarato` restano testo libero (`a.valore`), non "
        "un'entità risolta, coerentemente con la decisione già presa di "
        "non costruire `domini_dato` come tipo canonico."
    )
    lines.append(
        "- Non risolve `responsabile_azione` a persone canoniche: dove il "
        "documento non nomina una persona, l'arco resta ruolo_generico → "
        "azione."
    )
    lines.append(
        "- Non deduplica/cancella archi in caso di contraddizione tra "
        "documenti: tutti gli archi restano nell'output con la loro "
        "provenienza; la regola \"documento più recente vince\" va "
        "applicata da chi legge, come già in Cronistoria."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-layer", default="knowledge_layer_pilota.json")
    parser.add_argument("--estrazione", default="estrazione_pilota_cluster1_2.json")
    parser.add_argument("--output", default="relazioni_pilota.json")
    parser.add_argument("--report", default="relazioni_pilota_report.md")
    args = parser.parse_args()

    kl_path = Path(args.knowledge_layer)
    est_path = Path(args.estrazione)

    kl = json.loads(kl_path.read_text(encoding="utf-8"))
    estrazione = json.loads(est_path.read_text(encoding="utf-8"))

    archi_a = build_livello_a(kl)
    archi_b1 = build_livello_b1(kl)
    archi_b2 = build_livello_b2(estrazione)

    output = {
        "meta": {
            "descrizione": (
                "Passo derivato, prototipale — non una fase della pipeline. "
                "Gira dopo Estrazione e Knowledge Layer sullo stesso pilota "
                "(cluster 1, 2, 3, 4, 5, 9, 21)."
            ),
            "fonte_knowledge_layer": str(kl_path),
            "fonte_estrazione": str(est_path),
            "n_archi_livello_a": len(archi_a),
            "n_archi_livello_b1_ruolo_dichiarato": len(archi_b1),
            "n_archi_livello_b2_responsabile_azione": len(archi_b2),
        },
        "livello_a_co_menzione": archi_a,
        "livello_b1_ruolo_dichiarato": archi_b1,
        "livello_b2_responsabile_azione": archi_b2,
    }

    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = build_report(archi_a, archi_b1, archi_b2, kl_path, est_path)
    Path(args.report).write_text(report, encoding="utf-8")

    print(f"Livello A (co-menzionato-in): {len(archi_a)} archi")
    print(f"Livello B1 (ruolo_dichiarato): {len(archi_b1)} archi")
    print(f"Livello B2 (responsabile_azione): {len(archi_b2)} archi")
    print(f"Scritto: {args.output}")
    print(f"Scritto: {args.report}")


if __name__ == "__main__":
    main()
