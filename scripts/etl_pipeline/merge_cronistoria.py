#!/usr/bin/env python3
"""Merge Fase 5 (Cronistoria) — estensione cluster 9 (avanzamento) + avvisi qualita dati cluster 3,4,5,9."""
import json
import re
from pathlib import Path

BASE = Path("/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale")
cr = json.load(open(BASE / "cronistoria_pilota.json", encoding="utf-8"))
est = json.load(open(BASE / "estrazione_pilota_cluster1_2.json", encoding="utf-8"))

c9_keys = list(json.load(open("/sessions/happy-sharp-lovelace/work/estrazione_cluster9.json")).keys())

new_entries = []
for k in c9_keys:
    rec = est["avanzamento"][k]
    new_entries.append({
        "documento": k,
        "data": rec["data_documento"] if rec["data_documento"] else "Data non determinabile",
        "fonte_data": rec["data_fonte"],
        "decisioni": rec["decisioni"],
    })

timeline = cr["timeline_decisioni_cluster1"]

iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
dated = [e for e in timeline if iso_re.match(e["data"])]
undated = [e for e in timeline if not iso_re.match(e["data"])]

new_dated = [e for e in new_entries if iso_re.match(e["data"])]
new_undated = [e for e in new_entries if not iso_re.match(e["data"])]

dated_merged = sorted(dated + new_dated, key=lambda e: e["data"])
undated_merged = undated + new_undated  # append non-comparable dates at the end, as per existing convention

cr["timeline_decisioni_cluster1"] = dated_merged + undated_merged

# ---------------------------------------------------------------------------
# possibili_aggiornamenti_decisioni — pattern emerso dalle SAL cluster 9
# ---------------------------------------------------------------------------
cr.setdefault("possibili_aggiornamenti_decisioni", [])
cr["possibili_aggiornamenti_decisioni"].append({
    "tema": "Data di avvio del Pilota Reclami",
    "evoluzione": [
        {"data": "2025-10-22", "documento": "Documenti/0. Piano/Bludigit - Data Governance - SAL 20251022 v1.pptx",
         "stato": "Identificazione Pilota in attesa (23/10); in attesa riscontro su ambito"},
        {"data": "2025-11-10", "documento": "Documenti/0. Piano/Bludigit - Data Governance - SAL 20251110 v1 rev021.pptx",
         "stato": "Pilota orientato su area Commerciale/Reclami; perimetro ancora da confermare, in attesa riscontro gruppo Data Governance"},
        {"data": "2025-12-12", "documento": "Documenti/0. Piano/Bludigit - Data Governance - SAL 20251212 v3.pptx",
         "stato": "Richiesta ripianificazione avvio Pilota da parte area Reclami; nuova finestra: ultima settimana di gennaio (incontri) e febbraio (formazione/configurazione)"},
        {"data": "2026-01-09", "documento": "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx",
         "stato": "Confermata ripianificazione: formazione dal 22/01, censimento a febbraio; avvio Pilota da ultima settimana di gennaio"},
        {"data": "2026-05-08", "documento": "Documenti/Slide Barra DG -08052026 v2.pptx",
         "stato": "Nomina ufficiale Data Owner realizzata; avvio Pilota Reclami con coinvolgimento stakeholder indicato come prossimo passo — a questa data il pilota risulta quindi già in fase avanzata/nomine completate"},
    ],
    "nota": "La data di avvio del Pilota Reclami è stata ripianificata più volte tra ottobre 2025 e gennaio 2026 (vedi documenti SAL). Regola 'documento più recente vince' da applicare da chi legge.",
})

# ---------------------------------------------------------------------------
# avvisi_qualita_dati — nuovi avvisi da cluster 3, 4, 5, 9
# ---------------------------------------------------------------------------
cr.setdefault("avvisi_qualita_dati", [])
cr["avvisi_qualita_dati"].extend([
    {
        "tipo": "duplicazione_contenuto",
        "descrizione": (
            "I 7 file .xlsx della cartella 'Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/' "
            "hanno un rendering markdown gemello nella sottocartella 'md_output/' con contenuto equivalente "
            "(stessi alberi decisionali DECISIONI/KNOWLEDGE/STOP, stessi ID D-01/D-02/K-01/K-02 ecc.). "
            "In Estrazione il record .md è stato duplicato anche sul percorso .xlsx (con nota nel campo 'argomento'); "
            "nel Knowledge Layer le menzioni di sistemi_tool/persone sono state registrate una sola volta "
            "(sul percorso .md) per evitare di raddoppiare il conteggio delle occorrenze."
        ),
        "documenti_coinvolti": [
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/Classificatore_v1.xlsx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/Contestazione lettura-complessivo.xlsx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/ContestazioneLettura_Lettura_Ordinaria_V00.xlsx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/ContestazioneLettura_Switch_V03.xlsx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/ContestazioneLettura_Voltura_V02.xlsx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/Mancati appuntamenti_richiesta servizi tecnici-v0.xlsx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/Mancati appuntamenti_servizi tecnici + preventivi esecuzione lavori-v1.xlsx",
        ],
    },
    {
        "tipo": "incoerenza_data",
        "descrizione": (
            "Il file 'Bludigit - Data Governance - SAL 20250109 v1.pptx' ha nel nome la data 09/01/2025, ma il "
            "testo interno della slide riporta esplicitamente 'Milano | 09 Gennaio 2026'. È stata usata la data "
            "dal testo (2026-01-09, fonte_data='testo') come da convenzione della pipeline (testo prevale su "
            "nome file/metadati), ma la discrepanza nel nome del file è degna di segnalazione a chi gestisce l'archivio."
        ),
        "documenti_coinvolti": ["Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx"],
    },
    {
        "tipo": "identificazione_incerta_persona",
        "descrizione": (
            "Le liste 'partecipanti' delle SAL Bludigit (cluster 9) riportano solo cognomi (es. 'Bili', 'Barroero', "
            "'Aprea', 'Vetromile', 'Tognoni'), senza nome completo nel testo della slide. 'Barroero' è stato "
            "associato all'entità preesistente 'Edoardo Barroero' per corrispondenza di cognome. 'Aprea' è stato "
            "associato a 'Domenico Aprea' incrociando il cognome con l'email 'Domenico.Aprea@italgas.it' citata nel "
            "documento 'Classificatore_v1.md' (cluster 3, contesto diverso: procedure Reclami) — è un'inferenza "
            "cross-documento, non una conferma esplicita nello stesso documento. 'Bili', 'Vetromile' e 'Tognoni' "
            "sono stati creati come entità persona con solo il cognome come nome_canonico, in attesa di eventuale "
            "disambiguazione con nome completo da altri documenti."
        ),
        "documenti_coinvolti": [
            "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx",
            "Documenti/0. Piano/Bludigit - Data Governance - SAL 20251110 v1 rev021.pptx",
            "Documenti/0. Piano/Bludigit - Data Governance - SAL 20260416 v1.pptx",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Classificatore_v1.md",
        ],
    },
    {
        "tipo": "abbreviazione_ambigua_sistema_tool",
        "descrizione": (
            "Nei documenti della procedura Reclami (cluster 3) il sistema 'GasOnLine' è abbreviato in modo "
            "incoerente tra documenti gemelli: 'GOL' in Classificatore_v1.md e nei tre 'ContestazioneLettura_*', "
            "ma 'G2G' (e anche testo pieno 'GasOnline') nei due 'Mancati appuntamenti_*'. È stata creata una sola "
            "entità 'GasOnLine' nel Knowledge Layer con alias multipli. L'abbreviazione 'G2G' qui usata NON è stata "
            "unificata con l'entità preesistente 'G2G' (contesto MAPPATURA DATO/ARERA, cluster 1/2), perché in "
            "quel contesto 'G2G' sembra riferirsi a un sistema diverso non ulteriormente specificato: la possibile "
            "sovrapposizione resta da verificare con il business."
        ),
        "documenti_coinvolti": [
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Classificatore_v1.md",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Mancati appuntamenti_richiesta servizi tecnici-v0.md",
            "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Mancati appuntamenti_servizi tecnici + preventivi esecuzione lavori-v1.md",
        ],
    },
    {
        "tipo": "variante_nome_persona",
        "descrizione": (
            "Il documento 'ITH CO 15-25.pdf' riporta 'Nunziangelo Ferrulli' come responsabile Relazioni "
            "Istituzionali e Affari Regolatori, mentre il documento 'ITH CO 06-25.pdf' (già in KB) riportava lo "
            "stesso ruolo come 'Nunzio Ferrulli'. Trattati come la stessa persona (alias aggiunto all'entità "
            "esistente 'nunzio-ferrulli'); nome legale completo non confermabile dai soli documenti disponibili."
        ),
        "documenti_coinvolti": [
            "Documenti/4. Mappatura dati vs BU/Documenti organizzativi/ITH CO 06-25.pdf",
            "Documenti/4. Mappatura dati vs BU/Documenti organizzativi/ITH CO 15-25.pdf",
        ],
    },
    {
        "tipo": "perimetro_accesso_non_trascritto_per_privacy",
        "descrizione": (
            "I file 'Accessi_Data_Platform_23092025.xlsx', 'Lista_utenti_workspace_prod_23092025.xlsx' e "
            "'utenti_attivi_prod.csv' (cluster 5) contengono elenchi nominativi di utenti con accesso a sistemi "
            "IT. Per non elevare impropriamente utenti ordinari del sistema a 'responsabili' nel Knowledge Layer, "
            "i nomi individuali presenti in questi elenchi NON sono stati trascritti come persone/ruoli: il campo "
            "'ruoli_responsabilita' di questi documenti in Estrazione è stato lasciato vuoto, con solo una "
            "descrizione aggregata del contenuto. Se in futuro serve un censimento nominativo degli accessi, va "
            "trattato come richiesta specifica separata dalla pipeline documentale di governance."
        ),
        "documenti_coinvolti": [
            "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/Accessi_Data_Platform_23092025.xlsx",
            "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/Lista_utenti_workspace_prod_23092025.xlsx",
            "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/utenti_attivi_prod.csv",
        ],
    },
])

cr.setdefault("meta", {})
cr["meta"]["nota_estensione_2026-08-04"] = (
    "Timeline estesa con gli 8 documenti avanzamento del cluster 9 (SAL/piano Bludigit); aggiunto un tema di "
    "possibili_aggiornamenti_decisioni sull'evoluzione della data di avvio del Pilota Reclami; aggiunti 6 nuovi "
    "avvisi_qualita_dati relativi ai cluster 3, 4, 5, 9."
)
cr["meta"]["n_timeline_decisioni_cluster1"] = len(cr["timeline_decisioni_cluster1"])
cr["meta"]["n_possibili_aggiornamenti_decisioni"] = len(cr["possibili_aggiornamenti_decisioni"])
cr["meta"]["n_avvisi_qualita_dati"] = len(cr["avvisi_qualita_dati"])

Path(BASE / "cronistoria_pilota.json").write_text(json.dumps(cr, ensure_ascii=False, indent=2), encoding="utf-8")
print("timeline:", len(cr["timeline_decisioni_cluster1"]),
      "| possibili_aggiornamenti_decisioni:", len(cr["possibili_aggiornamenti_decisioni"]),
      "| avvisi_qualita_dati:", len(cr["avvisi_qualita_dati"]))
