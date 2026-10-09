import json, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    data = json.load(f)

docA = "Presentazioni/0_Nomina/Presentazione Data Governance.pptx"
docB = "Presentazioni/Bludigit/Data Governance - Meeting DF_V5.pptx"
docC = "Presentazioni/Bludigit/Team_Platma_v0.pptx"

data["contenuto"][docA] = {
    "sotto_tipo": "altro",
    "argomento": (
        "Presentazione introduttiva del progetto di Data Governance (Bludigit, maggio 2026): framework generale, "
        "deliverable, ruoli (Data Owner, Data Steward), piano di nomine tramite circolare (entro giugno 2026), "
        "matrice domini/sottodomini per PdR/Clienti Finali e Impianti di riduzione/RTU e Rete, effort di progetto "
        "(engagement Data Owner/Steward), piano temporale (Settembre 2025 -> Giugno: nomine, formazione, partenza "
        "Wave2 su dichiarazione ARERA, partenza Wave3), catalogo corsi di formazione, definizione regole di Data "
        "Quality, catalogo/glossario/lineage, mascheramento e access management, KPI/KQI. Sembra una versione "
        "precedente/introduttiva del percorso poi confluito nel piano Italgas Reti v14 (footer 12/07/2026) e nella "
        "matrice domini piu' ampia -- utile per ricostruire l'evoluzione del progetto nel tempo."
    ),
    "processi_attivita": [
        "Individuazione perimetri dati di business e associazione a figure di Owner e Steward",
        "Formalizzazione Data Owner e Data Steward",
        "Compilazione e descrizione del patrimonio informativo (catalogo, lineage, glossario)",
        "Utilizzo di strumenti GenAI per interrogazione e presidio del dato",
        "Formazione utenti business e definizione controlli di qualita' sui dati",
        "Nomina di Data Owner e Data Steward tramite circolare entro giugno 2026",
        "Piano a wave: Wave2 su dominio dichiarazione ARERA, poi Wave3, con estensione ad altri domini in base a priorita' (stanze digitali, demand)",
        "Definizione delle regole di Data Quality (completezza, coerenza, accuratezza, tempestivita') e monitoraggio periodico",
        "Costruzione di Catalogo, Glossario e Lineage dei dati",
        "Formazione Data Owner/Steward su strumenti (Databricks, Power BI, AI) tramite catalogo corsi dedicato",
        "Mascheramento dati sensibili (PII) e gestione accessi (Access Management)",
        "Definizione di KPI e KQI per misurare l'efficacia delle iniziative di Data Governance",
    ],
    "ruoli_responsabilita": [
        "Data Owner - responsabile strategico e proprietario del dato come asset aziendale; decide su significato e uso autorizzato dei dati del dominio",
        "Data Steward - esperto operativo del dominio, individuato dal Data Owner in base alla complessita' del perimetro; presidio operativo, gestione e descrizione del patrimonio informativo",
    ],
    "sistemi_tool_citati": [
        "Databricks per formazione pratica e query SQL",
        "Power BI per formazione pratica e dashboard",
        "Genie per catalogazione e hackathon (arricchimento metadati)",
    ],
    "riferimenti_normativi": [
        "Dichiarazione ARERA per dataset dominio dichiarazione obbligatoria (Wave2)",
    ],
    "versione_data_validita": "Maggio 2026 (testo: titolo 'Data Governance Maggio 2026'; giorno non specificato)",
    "versione_data_fonte": "testo",
}

data["contenuto"][docB] = {
    "sotto_tipo": "altro",
    "argomento": (
        "Presentazione metodologica su Data Governance applicata alle 'Stanze' (progetti agili di sviluppo dati) e "
        "al 'Demand' (richieste business): principi DG, pain point attuali (catalogo non navigabile, responsabilita' "
        "non formalizzate, discovery da zero ad ogni stanza), playbook PRIMA/DURANTE/DOPO per applicare la "
        "governance nelle stanze, processo di gestione delle richieste business (Demand) con Comitato DG&AI, "
        "prossimi passi (commitment del business, prioritizzazione stanze, formazione Data User), matrice "
        "domini/funzioni (IG Reti), concetto di Data Product, catalogo corsi di formazione, funzionalita' attivate "
        "su Data Platform (Data Quality, Data Lineage, Metadata, Access Management, Microsoft Entra ID). "
        "Nota: il documento e' denominato 'DF_V5' -- sembra la continuazione della serie di meeting Bludigit gia' "
        "presente nel cluster 1 (DF, DF_V2, DF_V3, DF_V4), ma e' stato catalogato in un cluster diverso (21) "
        "dall'algoritmo di clustering, probabilmente per deriva semantica del contenuto verso un taglio piu' "
        "metodologico/playbook. Segnalato come osservazione, non ancora verificato con Lorenzo."
    ),
    "processi_attivita": [
        "Definizione playbook Stanze: PRIMA (preparazione dominio, nomina Owner/Steward, formazione referenti), DURANTE (referenti attivi, catalogo aggiornato, dataset come data product), DOPO (formalizzazione ownership, presidio evolutivo, continuita' tra MVP1 e MVP2)",
        "Gestione delle richieste business (Demand) tramite Comitato DG&AI, con valutazione se sviluppabili in autonomia (Self-BI) o tramite sviluppo guidato",
        "Commitment del Business: ottenere commitment top management, nomina figure business, pianificazione attivita' sui perimetri stabiliti",
        "Prioritizzazione delle Stanze Data Factory in base a readiness del dato e complessita'",
        "Formazione Data User: programmi, materiali, sessioni di training e knowledge transfer",
        "Introduzione del concetto di Data Product con strumenti dedicati (Canvas, Data Product Owner, Referente Tecnico, Data Contract)",
    ],
    "ruoli_responsabilita": [
        "Data Owner - responsabile strategico e proprietario del dato; decide su significato e uso dei dati del dominio",
        "Data Steward - esperto operativo del dominio; gestisce dataset, documenta requisiti, aggiorna il Dizionario Dati Aziendale",
        "Comitato DG&AI - valuta le richieste business (Demand) e abilita lo sviluppo Self-BI tramite formazione dedicata",
        "Data Product Owner - responsabilita' su qualita', evoluzione e valore del Data Product",
        "Referente Tecnico - responsabile dell'implementazione e manutenzione tecnica del Data Product",
    ],
    "sistemi_tool_citati": [
        "Databricks per strumenti operativi e SQL base",
        "Power BI per dashboard",
        "Copilot/Genie per strumenti operativi in stanza",
        "Microsoft Entra ID per Access Management",
    ],
    "riferimenti_normativi": [
        "Dichiarazione ARERA - dataset dominio dichiarazione obbligatoria",
    ],
    "versione_data_validita": "2026-04-07",
    "versione_data_fonte": "data_modifica_file (approssimata)",
}

data["contenuto"][docC] = {
    "sotto_tipo": "altro",
    "argomento": (
        "Presentazione di sinergia tra il progetto Data Governance e il team Piattaforme (Platma): pain point "
        "attuali (richieste dati/report non strutturate, accessi e licenze SAP da rivedere, assenza di ownership "
        "formale), proposta di sinergia in 3 passi (validazione del significato dei campi chiave partendo dal "
        "perimetro Reclami, condivisione documentazione funzionale esistente es. Salesforce/SAP, validazione dei "
        "perimetri informativi per dominio), prossimi passi (supporto a knowledge extraction e test/validazione "
        "delle descrizioni AI su fonti complesse come SAP, confronto sulle regole di Data Quality dopo il "
        "coinvolgimento del business su Reclami/ARERA, commitment del Business). Contiene anche matrice "
        "domini/funzioni e concetto di Data Product, in comune con altre presentazioni DG. Nota: il testo contiene "
        "un'annotazione informale ('? potrebbe non esserci nulla in termine di documentazione - da capire con "
        "Maurizio') che sembra una nota di lavoro non finalizzata, non una decisione -- 'Maurizio' non e' stato "
        "aggiunto come entita' persona per ambiguita' (nome singolo, nessun cognome, non distinguibile)."
    ),
    "processi_attivita": [
        "Proposta di sinergia tra Data Governance e team Piattaforme: validazione del significato dei campi chiave nei sistemi sorgente, partendo dal perimetro Reclami",
        "Condivisione di documentazione funzionale/dizionari dati esistenti (es. Salesforce, SAP) per accelerare la catalogazione AI",
        "Validazione dei perimetri informativi per dominio, per strutturare il layer Databricks in Data Product navigabili",
        "Knowledge extraction: identificazione fonti informative e recupero contesto mancante (documentazione, interviste ai referenti), prioritizzando i dataset piu' utilizzati",
        "Test e validazione delle descrizioni generate dall'AI su fonti dati complesse (es. SAP), tramite verifica su campione rappresentativo (~100 campi, perimetro Reclami)",
        "Confronto sulle regole di Data Quality dopo il coinvolgimento del business sui perimetri DG (Reclami, stanza ARERA)",
    ],
    "ruoli_responsabilita": [
        "Data Owner - responsabilita' esplicita del dominio sulle decisioni di utilizzo, punto di riferimento per disambiguare interpretazioni divergenti",
        "Team Piattaforme - detiene la conoscenza implicita dei sistemi sorgente da rendere esplicita e riusabile",
    ],
    "sistemi_tool_citati": [
        "Databricks per strutturare i dati in Data Product",
        "Salesforce per dizionari dati esistenti",
        "SAP per dizionari dati esistenti e possibile revisione delle licenze",
        "Tibco - servizi citati come esempio di data product",
    ],
    "riferimenti_normativi": [
        "Dichiarazione ARERA - possibile stanza futura per il confronto sulle regole di Data Quality",
    ],
    "versione_data_validita": "2026-03-06",
    "versione_data_fonte": "data_modifica_file (approssimata)",
}

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json"), "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Documenti contenuto totali:", len(data["contenuto"]))
