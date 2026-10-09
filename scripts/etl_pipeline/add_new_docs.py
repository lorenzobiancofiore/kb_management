import json, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    data = json.load(f)

doc1_path = "Presentazioni/DG_Italgas_Piano_v16_DeSi.html"
doc2_path = "Presentazioni/DG_Acqua_Strategia_Governance_v2.html"

doc1 = {
    "sotto_tipo": "altro",
    "argomento": (
        "Presentazione del piano strategico 2026-2027 per la Data Governance di Italgas Reti: "
        "punto di partenza (345 utenti attivi su Databricks AI, gap di governo e di layer semantico), "
        "tre figure di ruolo (Data Owner, Data Steward, Data User & Super-User), matrice domini/sottodomini "
        "(3 domini, 36 sottodomini, 4 funzioni coinvolte, 18 Data Owner), piano di roll-out a 9 wave "
        "(Settembre 2026 -> Giugno 2027) e richiesta di via libera per l'avvio del progetto da settembre 2026. "
        "Nota di qualita' dati: il nome del file indica 'v16' ma il footer del documento riporta "
        "'v14 (De.Si.) -- 12/07/2026' -- possibile disallineamento di versionamento, da verificare con l'autore."
    ),
    "processi_attivita": [
        "Formalizzazione delle tre figure Data Owner, Data Steward, Data User & Super-User",
        "Costruzione del layer semantico di dominio come attivita' fondante di ogni wave",
        "Certificazione del dominio dati e definizione delle regole di Data Quality prioritarie (max 10 per sottodominio)",
        "Definizione dei profili di accesso (chi accede a quali dati e cosa puo' fare)",
        "Roll-out a wave del framework di governance: 9 wave da Settembre 2026 a Giugno 2027",
        "Validazione dei Genie Space creati dal business durante la certificazione del dominio",
        "Formazione e allineamento con Organizzazione/People sulle nuove figure di governance",
        "Governance federata con Governance Council per feedback dalle linee e definizione di innovazione e standard trasversali",
        "Richiesta di approvazione del progetto e avvio del roll-out da settembre 2026",
    ],
    "ruoli_responsabilita": [
        "Data Owner - responsabile del dominio: decide chi accede ai dati, approva le definizioni, garantisce l'affidabilita' del dato",
        "Data Steward - esperto operativo: descrive i dati, certifica il contenuto, definisce le regole di qualita', supporta il Data Owner sugli accessi",
        "Data User & Super-User - utilizzatori quotidiani del dato; i Super-User costruiscono analisi e Genie Space in autonomia",
        "Governance Council - organo di governance federata; riceve feedback dalle linee e definisce innovazione, standard e layer semantico",
        "Resp. Metering Mass Market - Data Owner proposto per Anagrafiche Contatore, Servizi tecnici MM, Allarmi MM, Telegestione",
        "Resp. Metering Grandi Utenze - Data Owner proposto per Anagrafiche Contatore, Servizi tecnici GU, Allarmi GU",
        "Resp. Processo Letture - Data Owner proposto per Servizi tecnici PROLET, Letture",
        "Resp. Nimbus - Data Owner proposto per NIMBUS",
        "Resp. Commercial Operations - Data Owner proposto per Anagrafiche clienti, Accertamento Documentale, Servizi tecnici alla clientela, Servizi commerciali",
        "Resp. Customer Service & Special Care - Data Owner proposto per Pratiche Reclami",
        "Resp. Contact Center - Data Owner proposto per Pratiche Contact Center",
        "Resp. Billing - Data Owner proposto per Fatturazione",
        "Resp. Settlement - Data Owner proposto per Settlement",
        "Resp. Eccellenza Operativa - Data Owner proposto per Anagrafica PDR",
        "Resp. Centro Integrato di Supervisione - Data Owner proposto per Pronto Intervento (dominio PdR/Clienti)",
        "Resp. Remote Control & Automation - Data Owner proposto per Anagrafiche RTU, IoT (dominio Impianti/RTU)",
        "Resp. Centro di Comando e Controllo Impianti - Data Owner proposto per Allarmi, Conduzione Allarmi",
        "Resp. Odorizzazione - Data Owner proposto per Odorizzante",
        "Resp. Gestione Impianti - Data Owner proposto per Anagrafica Impianti, Servizi di Manutenzione",
        "Resp. Protezione Catodica - Data Owner proposto per Anagrafiche asset, Servizi di Manutenzione",
        "Resp. Remote Control & Automation - Data Owner proposto per IoT Pegaso (dominio Impianti/RTU, funzione APT)",
        "Resp. Metering City Gate - Data Owner proposto per IoT Telettura REMI",
        "Resp. Cartografia - Data Owner proposto per Anagrafiche asset, Geometria e Sottoreti (dominio Rete)",
        "Resp. Gestione e Contenimento Emissioni Gas - Data Owner proposto per Ricerca fughe, Smart Maintenance",
        "Resp. Normativa - Data Owner proposto per Pronto Intervento (dominio Rete)",
    ],
    "sistemi_tool_citati": [
        "Databricks per ambiente centrale dati e AI, con Medallion layer operativo",
        "Genie Space per analisi self-BI e query sui dati",
        "Microsoft 365 Copilot per licenze e attivazione AI (1691 licenze, 908 Italgas Reti)",
        "Glossario, Catalogo, Ruoli, Data Quality come tool di governance configurati in piattaforma",
    ],
    "riferimenti_normativi": [],
    "versione_data_validita": "2026-07-12",
    "versione_data_fonte": "testo",
}

doc2 = {
    "sotto_tipo": "altro",
    "argomento": (
        "Presentazione della strategia di Data Governance per il perimetro Acqua (Acqualatina, Siciliacque, Nepta): "
        "stato attuale (17 Data Owner identificati, 10 domini, 16 sottodomini, 32 tabelle/1.070 campi catalogati), "
        "tre figure di governance (Data Owner, Data Steward -- in transizione presidiato dal team DG/Federico Foieni, "
        "Data User), roadmap giugno-dicembre 2026, proposta nominativa dei Data Owner per dominio/societa', e una "
        "sezione action item dalla call del 3 giugno 2026 con owner nominativi (Lorenzo Biancofiore, Federico Foieni, "
        "Team DG). Nota: contiene elementi tipici di verbale/avanzamento (action item con responsabile) oltre al "
        "contenuto descrittivo -- caso simile a 'Workshop 1 APT.docx' gia' incontrato nel pilota (documento ibrido "
        "contenuto/avanzamento). Nota di qualita' dati: il documento riporta due date di aggiornamento diverse "
        "('Aggiornato al 10 giugno 2026' in testata, 'Aggiornato al 3 giugno 2026' nella sezione roadmap) -- usata "
        "la data di testata come versione_data_validita."
    ),
    "processi_attivita": [
        "Identificazione dei Data Owner per il perimetro Acqua (17 nominativi su 3 societa')",
        "Catalogazione di 32 tabelle e 1.070 campi con metadatazione LLM e revisione umana",
        "Definizione del modello di governance: un Data Owner per societa' per dominio, domini definiti sulla matrice processi delle societa' idriche",
        "Formazione Data Owner (luglio-agosto 2026) su framework, strumenti e Access Management",
        "Formazione Data User (da settembre 2026) su Self-BI, ricerca dati e AI code",
        "Organizzazione delle classi formative (2-3 sessioni per ~7 Data Owner su 3 societa')",
        "Metadatazione con LLM: generazione automatica descrizioni, tracciamento correzioni manuali, validazione da parte degli Owner limitata al livello Platinum",
        "Wave di governance e catalogazione: Wave 1 (fine giugno/Q3 2026), Wave 2 (fine Q3/inizio Q4 2026)",
        "Formalizzazione dell'ingaggio dei Data Owner (Lorenzo, 4 AD, HR) prevista per inizio luglio 2026",
    ],
    "ruoli_responsabilita": [
        "Data Owner - responsabile strategico, proprietario del dato come asset; un Data Owner per societa' per dominio; approva catalogazione, regole di qualita', accessi",
        "Data Steward - esperto operativo del dominio; in via transitoria presidiato dal team DG (Federico Foieni), poi affidato a figure IT coinvolte nell'integrazione",
        "Data User - utilizzatore del dato in Self-BI dopo che il proprio dominio e' stato coperto da una wave di governance",
        "Federico Foieni - responsabile del primo perimetro dati e della Wave 2 (Trading & Gestion); condividera' il piano di integrazione con le numeriche; presidio del team DG a fine progetto",
        "Lorenzo Biancofiore - responsabile, con 4 AD e HR, della formalizzazione dell'ingaggio dei Data Owner",
        "Lorenzo Biancofiore - responsabile, con Federico Foieni, dell'aggiornamento delle slide del piano e della correzione della data di formalizzazione e della nomenclatura Data User/Data Steward (action item da call 3 giugno 2026)",
        "Federico Foieni - responsabile della condivisione del piano di integrazione con le numeriche, mappa applicativa per dominio (action item da call 3 giugno 2026)",
        "Team DG - responsabile della definizione dell'organizzazione delle classi formative, suddivisione dei ~7 Data Owner in 2-3 sessioni (action item da call 3 giugno 2026)",
        "Ettore Ippolito - proposto Data Owner Acqualatina per il dominio Gestione asset idrici",
        "Francesco Iervolino - proposto Data Owner Siciliacque per il dominio Gestione asset idrici",
        "Diego Russo - proposto Data Owner Nepta per il dominio Gestione asset idrici",
        "Nicola Anelli - proposto Data Owner Acqualatina per i domini Gestione della clientela acqua e Finance",
        "Simona Messineo - proposto Data Owner Siciliacque per i domini Gestione della clientela acqua e Metering",
        "Andrea Gambardella - proposto Data Owner Nepta per il dominio Gestione della clientela acqua",
        "Lucrezia Coccia - proposto Data Owner Acqualatina per il dominio Metering",
        "Raffaele Esposito - proposto Data Owner Nepta per il dominio Metering",
        "Loredana Capuani - proposto Data Owner Acqualatina per il dominio Sistemi di gestione HSEQE",
        "Graziella Russo - proposto Data Owner Siciliacque per il dominio Sistemi di gestione HSEQE",
        "Nacchia Bonaventura - proposto Data Owner Nepta per il dominio Sistemi di gestione HSEQE",
        "Silvia Coccato - proposto Data Owner Acqualatina per il dominio Acquisti",
        "Alberto De Simone - proposto Data Owner Siciliacque per il dominio Acquisti",
        "Salvatore Toro - proposto Data Owner Siciliacque per il dominio Finance",
        "Monica Tessaro - proposto Data Owner Nepta per il dominio Finance",
        "Edmondo Di Lauro - proposto Data Owner Acqualatina e Nepta per il dominio HR",
        "Calogero Montalbano - proposto Data Owner Siciliacque per il dominio HR",
    ],
    "sistemi_tool_citati": [
        "Unity Catalog per catalogazione dati (descrizioni, tag, lineage)",
        "Databricks per Self-BI, dashboard e AI code",
        "Genie per query e report self-BI",
        "ABAC/ACL per permessi di accesso configurati e mantenuti dal Data Steward",
    ],
    "riferimenti_normativi": [],
    "versione_data_validita": "2026-06-10",
    "versione_data_fonte": "testo",
}

data["contenuto"][doc1_path] = doc1
data["contenuto"][doc2_path] = doc2

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json"), "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Documenti contenuto totali:", len(data["contenuto"]))
print("Documenti avanzamento totali:", len(data["avanzamento"]))
