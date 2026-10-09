import json, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    est = json.load(f)
with open(os.path.join(BASE, "knowledge_layer_pilota.json")) as f:
    kl = json.load(f)

# --- 1. Timeline decisioni (cluster 1, avanzamento) ---
timeline = []
for path, r in est["avanzamento"].items():
    timeline.append({
        "documento": path,
        "data": r.get("data_documento"),
        "fonte_data": r.get("data_fonte"),
        "decisioni": r.get("decisioni") or [],
    })
timeline.sort(key=lambda x: x["data"] or "9999")

# --- 2. Ultima menzione per entità (Knowledge Layer) — mai un'interpretazione, solo max(data) ---
def sortable(d):
    # le date non-ISO (testuali) vengono messe in fondo come meno affidabili per l'ordinamento automatico
    if not d:
        return "0000-00-00"
    if len(d) == 10 and d[4] == "-" and d[7] == "-":
        return d
    return "0000-00-00"  # non ordinabile automaticamente

for categoria in ("persone", "sistemi_tool", "riferimenti_normativi"):
    for ent in kl[categoria]:
        menzioni_ordinabili = [m for m in ent["menzioni"] if sortable(m["data"]) != "0000-00-00"]
        if menzioni_ordinabili:
            ultima = max(menzioni_ordinabili, key=lambda m: sortable(m["data"]))
            ent["ultima_menzione"] = ultima
        else:
            ent["ultima_menzione"] = None  # nessuna data ordinabile disponibile

# --- 3. Possibili aggiornamenti/sostituzioni tra decisioni (INTERPRETAZIONE — da validare) ---
# Costruito leggendo manualmente la timeline sopra, non tramite matching automatico.
possibili_aggiornamenti = [
    {
        "tema": "Perimetro del pilota",
        "decisione_precedente": {"data": "2025-11-03", "documento": "Presentazioni/COMM/Data Governance - Meeting Commerciale v1.pptx", "testo": "Identificazione iniziale del perimetro pilota sull'area commerciale"},
        "decisione_successiva": {"data": "2025-11-19", "documento": "Presentazioni/COMM/Data Governance - Meeting Commerciale v5.pptx", "testo": "Applicazione della governance su Reclami come caso d'uso prioritario"},
        "eseguita_in": {"data": "2026-01-14", "documento": "Presentazioni/Barra/Data Governance - Meeting Barra v0.pptx", "testo": "Partenza pilota su Reclami il 22 gennaio con formazione"},
        "confidenza": "media-alta",
        "nota": "Il perimetro passa da 'area commerciale' generica a 'Reclami' come caso d'uso specifico, poi eseguito operativamente. Reclami è probabilmente un sotto-ambito di quell'area, quindi è più una specificazione che una vera contraddizione — ma è la versione più recente da considerare valida.",
    },
    {
        "tema": "Modalità di implementazione (wave / stanze / fast-track)",
        "decisione_precedente": {"data": "2025-10-14", "documento": "Presentazioni/ORG/Data Governance - Meeting Org v09.pptx", "testo": "Adottare un approccio ibrido che combina wave DG su domini chiave, sinergie con stanze ad alta priorità e fast track per opportunità urgenti"},
        "decisione_successiva": {"data": "2026-02-23", "documento": "Presentazioni/Bludigit/Data Governance - Meeting DF_V4.pptx", "testo": "Adozione di approcci multi-dominio waves, fast-track, e minimal setup a seconda dei contesti"},
        "confidenza": "media",
        "nota": "Framework stabile nel tempo (wave + fast-track ricorrono in quasi tutti i documenti intermedi), ma a febbraio si aggiunge esplicitamente una terza modalità ('minimal setup') non presente nella formulazione originale di ottobre. Sembra un'estensione del framework più che una sostituzione.",
    },
    {
        "tema": "Formalizzazione dei ruoli Data Owner / Data Steward",
        "decisione_precedente": {"data": "2025-11-19", "documento": "Presentazioni/COMM/Data Governance - Meeting Commerciale v5.pptx", "testo": "Formalizzazione di ruoli con chiara titolarità aziendale"},
        "decisione_successiva": {"data": "2026-02-23", "documento": "Presentazioni/Bludigit/Data Governance - Meeting DF_V4.pptx", "testo": "Ruoli di Data Owner e Data Steward formalizzati e obbligatori"},
        "confidenza": "media-alta",
        "nota": "Il linguaggio si irrigidisce nel tempo: da 'chiara titolarità' (formalizzazione) a 'obbligatori' — sembra un inasprimento della decisione, non solo una riformulazione.",
    },
    {
        "tema": "Uso di GenAI per l'analisi dati",
        "decisione_precedente": {"data": "2026-01-27", "documento": "Presentazioni/Bludigit/Data Governance - Meeting DF_V3.pptx", "testo": "Adottare strategia di accelerazione tramite GenAI per la compilazione accelerata dei metadati"},
        "decisione_successiva": {"data": "2026-02-12", "documento": "Presentazioni/Barra/Data Governance - v2.pptx", "testo": "Pianificazione rolling a ondate di priorità (Febbraio, Aprile, Giugno 2026, poi maintenance)"},
        "confidenza": "bassa-media",
        "nota": "Non è una sostituzione: la decisione di febbraio aggiunge un calendario operativo alla strategia GenAI già decisa, è un arricchimento non una contraddizione.",
    },
]

avviso_qualita_dati = {
    "descrizione": "Data Governance - Meeting DF_V4.pptx e Data Governance - Meeting DF_V4 (1).pptx hanno contenuto quasi identico e mtime a un giorno di distanza (23 e 24 febbraio 2026) — probabile file duplicato/rinominato, non una vera evoluzione della decisione in un giorno. Da NON trattare come due punti distinti della cronologia.",
    "documenti": [
        "Presentazioni/Bludigit/Data Governance - Meeting DF_V4.pptx",
        "Presentazioni/Bludigit/Data Governance - Meeting DF_V4 (1).pptx",
    ],
}

avviso_versionamento_italgas = {
    "descrizione": "Il nome del file 'DG_Italgas_Piano_v16_DeSi.html' indica versione v16, ma il footer del documento riporta 'v14 (De.Si.) — 12/07/2026'. Possibile disallineamento tra nomenclatura file e numerazione interna delle versioni — da verificare con l'autore prima di usare questo documento come riferimento di versione più recente in modo automatico.",
    "documenti": ["Presentazioni/DG_Italgas_Piano_v16_DeSi.html"],
}

avviso_doppia_data_acqua = {
    "descrizione": "Il documento 'DG_Acqua_Strategia_Governance_v2.html' riporta due date di aggiornamento diverse: 'Aggiornato al 10 giugno 2026' in testata e 'Aggiornato al 3 giugno 2026' nella sezione roadmap (03 — Piano Temporale). Per versione_data_validita è stata usata la data di testata (10 giugno, più recente e più generale); la sezione roadmap potrebbe non essere stata aggiornata all'ultimo giro.",
    "documenti": ["Presentazioni/DG_Acqua_Strategia_Governance_v2.html"],
}

nota_documenti_ibridi_fuori_timeline = {
    "descrizione": (
        "'DG_Italgas_Piano_v16_DeSi.html' e 'DG_Acqua_Strategia_Governance_v2.html' sono classificati come 'contenuto' "
        "(presentazioni strategiche), non 'avanzamento' — quindi NON entrano nella timeline_decisioni_cluster1 sopra, "
        "che è scoped ai soli documenti di avanzamento. Tuttavia, come già visto con 'Riunioni/Workshop 1 APT.docx', "
        "sono documenti ibridi: contengono elementi tipici di avanzamento. In particolare 'DG_Acqua_Strategia_Governance_v2.html' "
        "ha una sezione '08 — Prossime Azioni' con 4 action item datati (call del 3 giugno 2026, owner: Lorenzo Biancofiore/"
        "Federico Foieni, Federico Foieni, Team DG, Tutti) — informazione rilevante per capire 'come si è arrivati a una "
        "decisione', ma oggi non è tracciata nella cronistoria per scelta di scope. Segnalato come domanda di design aperta: "
        "se e come estendere la cronistoria a questo tipo di contenuto ibrido."
    ),
    "documenti": [
        "Presentazioni/DG_Italgas_Piano_v16_DeSi.html",
        "Presentazioni/DG_Acqua_Strategia_Governance_v2.html",
        "Riunioni/Workshop 1 APT.docx",
    ],
}

avviso_correzione_perimetro_cluster21 = {
    "descrizione": (
        "Correzione di perimetro (31 luglio 2026): i primi 2 documenti nuovi (DG_Italgas_Piano_v16_DeSi.html, "
        "DG_Acqua_Strategia_Governance_v2.html) erano stati assegnati dalla catalogazione al cluster 21 — un cluster "
        "mai toccato dal pilota originale di Knowledge Layer/Cronistoria (scope: cluster 1 avanzamento + cluster 2 "
        "contenuto). Lorenzo ha rilevato l'incongruenza. Correzione applicata su sua indicazione ('Completa il "
        "cluster 21 per intero'): estratti anche i 3 documenti preesistenti del cluster 21 (Presentazione Data "
        "Governance.pptx, Data Governance - Meeting DF_V5.pptx, Team_Platma_v0.pptx), portando il cluster 21 a "
        "copertura completa (5/5 documenti). Resta invece deliberatamente non affrontato un gap distinto nel cluster 2 "
        "(contenuto): 2 documenti riclassificati nel cluster (Catodica PDF, Matrice Domini Unità.xlsx) non sono mai "
        "stati estratti — 14/16 documenti coperti, non ancora azionato."
    ),
    "documenti": [
        "Presentazioni/0_Nomina/Presentazione Data Governance.pptx",
        "Presentazioni/Bludigit/Data Governance - Meeting DF_V5.pptx",
        "Presentazioni/Bludigit/Team_Platma_v0.pptx",
    ],
}

avviso_df_v5_serie = {
    "descrizione": (
        "'Data Governance - Meeting DF_V5.pptx' è nominato come continuazione della serie di meeting Bludigit "
        "già presente nel cluster 1 (DF, DF_V2, DF_V3, DF_V4 — tutti classificati 'avanzamento'), ma la "
        "catalogazione lo ha assegnato al cluster 21 (contenuto) insieme ad altri documenti su temi diversi "
        "(governance/owner/qualità/dominio). Se si tratta davvero della quinta puntata della stessa serie di SAL, "
        "potrebbe contenere decisioni di avanzamento rilevanti per la timeline_decisioni_cluster1 che oggi non vi "
        "compaiono, essendo stato estratto con lo schema 'contenuto'/'altro'. Non ancora verificato con Lorenzo — "
        "segnalato come domanda di design aperta, non come correzione già applicata."
    ),
    "documenti": ["Presentazioni/Bludigit/Data Governance - Meeting DF_V5.pptx"],
}

out = {
    "timeline_decisioni_cluster1": timeline,
    "possibili_aggiornamenti_decisioni": possibili_aggiornamenti,
    "avvisi_qualita_dati": [
        avviso_qualita_dati,
        avviso_versionamento_italgas,
        avviso_doppia_data_acqua,
        avviso_correzione_perimetro_cluster21,
        avviso_df_v5_serie,
        nota_documenti_ibridi_fuori_timeline,
    ],
}

with open(os.path.join(BASE, "cronistoria_pilota.json"), "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# aggiorna anche il knowledge layer con ultima_menzione
with open(os.path.join(BASE, "knowledge_layer_pilota.json"), "w") as f:
    json.dump(kl, f, ensure_ascii=False, indent=2)

print("Cronistoria pilota costruita.")
print("Possibili aggiornamenti individuati:", len(possibili_aggiornamenti))
