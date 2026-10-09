#!/usr/bin/env python3
"""Merge Fase 4 (Knowledge Layer) — estensione cluster 3,4,5,9."""
import json
import re
from pathlib import Path

BASE = Path("/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale")
kl = json.load(open(BASE / "knowledge_layer_pilota.json", encoding="utf-8"))

persone_by_id = {p["id"]: p for p in kl["persone"]}
sistemi_by_id = {s["id"]: s for s in kl["sistemi_tool"]}

def slug(name):
    s = name.lower()
    s = re.sub(r"[àá]", "a", s)
    s = re.sub(r"[èé]", "e", s)
    s = re.sub(r"[ìí]", "i", s)
    s = re.sub(r"[òó]", "o", s)
    s = re.sub(r"[ùú]", "u", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

def add_persona_menzione(existing_id, nome_canonico, documento, tipo_documento, data, fonte_data, contesto, alias_new=None):
    if existing_id and existing_id in persone_by_id:
        p = persone_by_id[existing_id]
        if alias_new and alias_new not in p["alias"] and alias_new != p["nome_canonico"]:
            p["alias"].append(alias_new)
    else:
        pid = slug(nome_canonico)
        if pid in persone_by_id:
            p = persone_by_id[pid]
        else:
            p = {"id": pid, "tipo": "persona", "nome_canonico": nome_canonico, "alias": [], "menzioni": [], "ultima_menzione": None}
            persone_by_id[pid] = p
            kl["persone"].append(p)
    p["menzioni"].append({
        "documento": documento,
        "tipo_documento": tipo_documento,
        "data": data,
        "fonte_data": fonte_data,
        "contesto": contesto,
    })
    if data and re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
        cur = p.get("ultima_menzione")
        if not cur or cur["data"] < data:
            p["ultima_menzione"] = p["menzioni"][-1]
    return p

def add_sistema_menzione(existing_id, nome_canonico, documento, tipo_documento, data, fonte_data, contesto, alias_new=None):
    if existing_id and existing_id in sistemi_by_id:
        s = sistemi_by_id[existing_id]
        if alias_new and alias_new not in s["alias"] and alias_new != s["nome_canonico"]:
            s["alias"].append(alias_new)
    else:
        sid = slug(nome_canonico)
        if sid in sistemi_by_id:
            s = sistemi_by_id[sid]
        else:
            s = {"id": sid, "tipo": "sistema_tool", "nome_canonico": nome_canonico, "alias": [], "menzioni": [], "ultima_menzione": None}
            sistemi_by_id[sid] = s
            kl["sistemi_tool"].append(s)
    s["menzioni"].append({
        "documento": documento,
        "tipo_documento": tipo_documento,
        "data": data,
        "fonte_data": fonte_data,
        "contesto": contesto,
    })
    if data and re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
        cur = s.get("ultima_menzione")
        if not cur or cur["data"] < data:
            s["ultima_menzione"] = s["menzioni"][-1]
    return s

D_ITHCO = "Documenti/4. Mappatura dati vs BU/Documenti organizzativi/"

# ---------------------------------------------------------------------------
# PERSONE — cluster 9 (avanzamento, partecipanti SAL Bludigit)
# ---------------------------------------------------------------------------
add_persona_menzione(None, "Bili", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx", "avanzamento", "2026-01-09", "testo", "partecipante alla riunione/SAL")
add_persona_menzione("edoardo-barroero", "Edoardo Barroero", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx", "avanzamento", "2026-01-09", "testo", "partecipante alla riunione/SAL (cognome 'Barroero')")
add_persona_menzione(None, "Domenico Aprea", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx", "avanzamento", "2026-01-09", "testo", "partecipante alla riunione/SAL (cognome 'Aprea'; identificazione come Domenico Aprea per inferenza da email citata in altro documento, vedi avvisi qualità dati)", alias_new="Aprea (cognome citato nelle SAL Bludigit)")
add_persona_menzione(None, "Vetromile", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx", "avanzamento", "2026-01-09", "testo", "partecipante alla riunione/SAL")
add_persona_menzione(None, "Tognoni", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20250109 v1.pptx", "avanzamento", "2026-01-09", "testo", "partecipante alla riunione/SAL")
add_persona_menzione(None, "Bili", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20251110 v1 rev021.pptx", "avanzamento", "2025-11-10", "testo", "partecipante alla riunione/SAL")
add_persona_menzione(None, "Domenico Aprea", "Documenti/0. Piano/Bludigit - Data Governance - SAL 20260416 v1.pptx", "avanzamento", "2026-04-16", "data_modifica_file (approssimata)", "partecipante alla riunione/SAL (cognome 'Aprea')")

# ---------------------------------------------------------------------------
# PERSONE — cluster 3 (ruoli_responsabilita da Classificatore_v1.md)
# ---------------------------------------------------------------------------
add_persona_menzione(None, "Domenico Aprea",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Classificatore_v1.md",
    "contenuto", None, "non determinabile",
    "citato in ruoli/responsabilità: Sviluppo Utenza: responsabile del change-of-address per richieste GDPR (da contattare via Domenico.Aprea@italgas.it)")
# duplicato: stesso record va replicato anche sul gemello xlsx (vedi merge estrazione)
add_persona_menzione(None, "Domenico Aprea",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/Classificatore_v1.xlsx",
    "contenuto", None, "non determinabile",
    "citato in ruoli/responsabilità: Sviluppo Utenza: responsabile del change-of-address per richieste GDPR (da contattare via Domenico.Aprea@italgas.it) [Nota: contenuto identico al rendering markdown gemello]")

# ---------------------------------------------------------------------------
# PERSONE — cluster 5 (circolari organizzative ITH CO 13-25 .. 20-25)
# ---------------------------------------------------------------------------
ithco = [
    ("ITH CO 13-25.pdf", [
        (None, "Crescenzo Napoletano", "Amministrazione e Bilancio - Crescenzo Napoletano"),
        (None, "Simone Allara", "Bilancio - Simone Allara"),
        (None, "Francesca Russo", "Ciclo Attivo e Passivo - Francesca Russo"),
        (None, "Sergio Cangialosi", "Contabilità Generale e Patrimoniale - Sergio Cangialosi"),
        (None, "Anna Maria Scaglia", "Investor Relations - Anna Maria Scaglia"),
        (None, "Paolo Dolci", "Sistemi di Controllo, Reporting e M&A - Paolo Dolci"),
        (None, "Massimiliano Silvestri", "Finanza - Massimiliano Silvestri"),
        (None, "Valeria Quaranta", "Group Controlling - Valeria Quaranta"),
    ]),
    ("ITH CO 14-25.pdf", [
        (None, "Silvia Caccia", "Employee Experience - Silvia Caccia"),
        (None, "Claudio Magni", "Development - Claudio Magni"),
        (None, "Benedetto Cafferini", "Group Organization & HR Operations - Benedetto Cafferini"),
        (None, "Riccardo Zinno", "HRBP - Riccardo Zinno"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
    ("ITH CO 15-25.pdf", [
        (None, "Leonardo D'Acquisto", "Relazioni Istituzionali Italia ed Europa - Leonardo D'Acquisto"),
        (None, "Gianni Rossetto", "Relazioni Istituzionali Locali - Gianni Rossetto"),
        (None, "Riccardo Carlini", "Tariffe - Riccardo Carlini"),
        (None, "Simone Viganò", "Affari Regolatori e Compliance - Simone Viganò"),
        ("nunzio-ferrulli", "Nunziangelo Ferrulli", "Chief Relazioni Istituzionali e Affari Regolatori Officer - Nunziangelo Ferrulli"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
    ("ITH CO 16-25.pdf", [
        (None, "Daniele Battaini", "International Scouting - Daniele Battaini"),
        (None, "Salvatore Boccuto", "Vendor Management & Sustainability - Salvatore Boccuto"),
        (None, "Giovanni Giampaolo", "Material Management - Giovanni Giampaolo"),
        (None, "Vittorio Petrone", "Procurement Excellence - Vittorio Petrone"),
        ("raffaella-marcuccio", "Raffaella Marcuccio", "Procurement Business Partner - Raffaella Marcuccio"),
        ("raffaella-marcuccio", "Raffaella Marcuccio", "Chief Procurement e Material Management Officer - Raffaella Marcuccio"),
        (None, "Federico Prosio", "Category Management Regolato - Federico Prosio"),
        (None, "Giusi Milena Di Bella", "Category Management Staff, IT, Innovation - Giusi Milena Di Bella"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
    ("ITH CO 17-25.pdf", [
        (None, "Valentina Piacentini", "Corporate Affairs - Valentina Piacentini"),
        (None, "Serena Picca", "Legale Concessioni e Appalti - Serena Picca"),
        (None, "Valentina Sandri", "Legale Gare e Territorio - Valentina Sandri"),
        (None, "Serenella Meloni", "Compliance, Anticorruzione, Penale e OdV - Serenella Meloni"),
        (None, "Camilla Dejana", "Legale Finance & Business Development - Camilla Dejana"),
        (None, "Alfredo Ligotti", "Legale Idrico - Alfredo Ligotti"),
        (None, "Giulia Marti", "Legale Efficienza Energetica e Contrattualistica - Giulia Marti"),
        (None, "Stefania D'Agnelli", "Legale Innovation & AI - Stefania D'Agnelli"),
        ("germana-mentil", "Germana Mentil", "General Counsel - Germana Mentil"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
    ("ITH CO 18-25.pdf", [
        (None, "Andrea Zlobec", "Security & Resilience - Andrea Zlobec"),
        (None, "Arcangelo Volpe", "Digital Energy Management - Arcangelo Volpe"),
        (None, "Sara Ruocco", "Real Estate Development - Sara Ruocco"),
        (None, "Mariagrazia Spadaro Norella", "Real Estate Operations - Mariagrazia Spadaro Norella"),
        (None, "Valerio Cocco", "Global Services - Valerio Cocco"),
        ("alessandro-menna", "Alessandro Menna", "Chief Group Security & Real Estate Officer - Alessandro Menna"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
    ("ITH CO 19-25.pdf", [
        (None, "Claudio Urciuolo", "Group Media Relations & Digital Communications - Claudio Urciuolo"),
        (None, "Susanna Tosti", "Brand Communications & Events - Susanna Tosti"),
        (None, "Mirko Cafaro", "Comunicazione Idrico - Mirko Cafaro"),
        (None, "Claudio Motta", "Comunicazione non Regolato - Claudio Motta"),
        (None, "Elena Perazzi", "Comunicazione BTL e Sponsorizzazioni - Elena Perazzi"),
        (None, "Marco Montanini", "Sostenibilità - Marco Montanini"),
        (None, "Katya Corvino", "Heritage Lab - Katya Corvino"),
        ("chiara-ganz", "Chiara Ganz", "Chief Relazioni Esterne e Sostenibilità Officer - Chiara Ganz"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
    ("ITH CO 20-25.pdf", [
        (None, "Laura Macciò", "Corporate Development e M&A - Laura Macciò"),
        ("lorenzo-romeo", "Lorenzo Romeo", "Strategy - Lorenzo Romeo"),
        ("lorenzo-romeo", "Lorenzo Romeo", "Chief Corporate Strategy Officer - Lorenzo Romeo"),
        (None, "Giorgio Segre", "Green Gas Development - Giorgio Segre"),
        ("peter-durante", "Peter Durante", "Chief People, Innovation & Transformation Officer - Peter Durante"),
    ]),
]

for fname, entries in ithco:
    doc = D_ITHCO + fname
    for existing_id, nome, ruolo_txt in entries:
        alias = nome if existing_id else None
        add_persona_menzione(existing_id, nome, doc, "contenuto", "2025-07-01", "testo",
                              f"citato in ruoli/responsabilità: {ruolo_txt}", alias_new=alias)

# ---------------------------------------------------------------------------
# SISTEMI_TOOL — cluster 3 (Reclami)
# ---------------------------------------------------------------------------
c3_docs_md = [
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Classificatore_v1.md",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Contestazione lettura-complessivo.md",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/ContestazioneLettura_Lettura_Ordinaria_V00.md",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/ContestazioneLettura_Switch_V03.md",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/ContestazioneLettura_Voltura_V02.md",
]
for d in c3_docs_md:
    add_sistema_menzione("salesforce", "Salesforce", d, "contenuto", None, "non determinabile", "citato tra i sistemi/tool della procedura Reclami")
    add_sistema_menzione("sap", "SAP", d, "contenuto", None, "non determinabile", "citato tra i sistemi/tool della procedura Reclami")
for d in c3_docs_md[2:]:  # i tre "ContestazioneLettura_*" citano anche MDM e GasOnLine (GOL)
    add_sistema_menzione("mdm", "MDM", d, "contenuto", None, "non determinabile", "citato tra i sistemi/tool della procedura Reclami")
    add_sistema_menzione(None, "GasOnLine", d, "contenuto", None, "non determinabile", "GasOnLine (GOL)", alias_new="GasOnLine (GOL)")
add_sistema_menzione(None, "GasOnLine", c3_docs_md[0], "contenuto", None, "non determinabile", "GasToGo/GasOnLine citati insieme nel Classificatore: GasOnLine (GOL)")
add_sistema_menzione(None, "GasToGo (GTG)", c3_docs_md[0], "contenuto", None, "non determinabile", "GasToGo (GTG)")
add_sistema_menzione("ampper", "AMPPER", c3_docs_md[0], "contenuto", None, "non determinabile", "AMPPER BILLING", alias_new="AMPPER BILLING")

c3_docs_mancati = [
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Mancati appuntamenti_richiesta servizi tecnici-v0.md",
    "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/md_output/Mancati appuntamenti_servizi tecnici + preventivi esecuzione lavori-v1.md",
]
for d in c3_docs_mancati:
    add_sistema_menzione("salesforce", "Salesforce", d, "contenuto", None, "non determinabile", "citato tra i sistemi/tool della procedura Reclami")
    add_sistema_menzione("sap", "SAP", d, "contenuto", None, "non determinabile", "citato tra i sistemi/tool della procedura Reclami")
    add_sistema_menzione(None, "GasOnLine", d, "contenuto", None, "non determinabile", "citato come 'GasOnLine (G2G)' / 'GasOnline' — vedi avvisi qualità dati per possibile confusione con l'entità G2G preesistente", alias_new="GasOnLine (G2G)")
    add_sistema_menzione(None, "G2B", d, "contenuto", None, "non determinabile", "G2B")

# gemelli xlsx di cluster 3: stessi sistemi_tool_citati, stesse menzioni ma su percorso xlsx
c3_pairs = {
    "Classificatore_v1.md": "Classificatore_v1.xlsx",
    "Contestazione lettura-complessivo.md": "Contestazione lettura-complessivo.xlsx",
    "ContestazioneLettura_Lettura_Ordinaria_V00.md": "ContestazioneLettura_Lettura_Ordinaria_V00.xlsx",
    "ContestazioneLettura_Switch_V03.md": "ContestazioneLettura_Switch_V03.xlsx",
    "ContestazioneLettura_Voltura_V02.md": "ContestazioneLettura_Voltura_V02.xlsx",
    "Mancati appuntamenti_richiesta servizi tecnici-v0.md": "Mancati appuntamenti_richiesta servizi tecnici-v0.xlsx",
    "Mancati appuntamenti_servizi tecnici + preventivi esecuzione lavori-v1.md": "Mancati appuntamenti_servizi tecnici + preventivi esecuzione lavori-v1.xlsx",
}
base_dir_c3 = "Documenti/8. Business Glossary/Doc_Excel_stanza_Reclami/"
# NOTA: per non gonfiare eccessivamente le menzioni con duplicati esatti (md + xlsx gemello),
# non ripetiamo qui le menzioni sistemi_tool sul percorso xlsx: la duplicazione di CONTENUTO
# è già segnalata nel record di Estrazione (campo argomento) e sarà evidenziata in Cronistoria
# come avviso di qualità dati, senza raddoppiare le menzioni nel Knowledge Layer.

# ---------------------------------------------------------------------------
# SISTEMI_TOOL — cluster 4 (formazione)
# ---------------------------------------------------------------------------
add_sistema_menzione("emmg", "EMMG",
    "Documenti/1. Attività tecniche/Documentazione per LLM/Metering/Other files/eMMG-analisiComponentiSistemaDaMonitorare_v3.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "eMMG (analisi componenti sistema da monitorare)", alias_new="eMMG")
add_sistema_menzione(None, "Metering",
    "Documenti/1. Attività tecniche/Documentazione per LLM/Metering/Other files/eMMG-analisiComponentiSistemaDaMonitorare_v3.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "Metering (area/dominio applicativo)")
add_sistema_menzione("databricks", "Databricks",
    "Documenti/2. Formazione/Corsi Databricks e PBI/Genie + AI-BI/Data Governance -  Formazione Databricks itg - Sessione AI-BI.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "Databricks per formazione AI-BI")
add_sistema_menzione("power-bi", "Power BI",
    "Documenti/2. Formazione/Corsi Databricks e PBI/Genie + AI-BI/Data Governance -  Formazione Databricks itg - Sessione AI-BI.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "Power BI per formazione AI-BI")
add_sistema_menzione(None, "AI-BI",
    "Documenti/2. Formazione/Corsi Databricks e PBI/Genie + AI-BI/Data Governance -  Formazione Databricks itg - Sessione AI-BI.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "sessione formativa AI-BI (Databricks/Power BI)")
add_sistema_menzione("databricks", "Databricks",
    "Documenti/2. Formazione/Corsi Databricks e PBI/Genie + AI-BI/Data Governance -  Formazione Databricks itg - Sessione Genie.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "Databricks per formazione Genie")
add_sistema_menzione("genie", "Genie",
    "Documenti/2. Formazione/Corsi Databricks e PBI/Genie + AI-BI/Data Governance -  Formazione Databricks itg - Sessione Genie.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "Genie per formazione")
add_sistema_menzione("genie", "Genie",
    "Documenti/2. Formazione/Formazione_AImReady/Academy_stream_DQ/Tabelle Corso Genie/demo_chinook/Demo_chinook.pptx",
    "contenuto", None, "data_modifica_file (approssimata)", "Genie (demo chinook per corso)")

# ---------------------------------------------------------------------------
# SISTEMI_TOOL — cluster 5 (workspace/circolari)
# ---------------------------------------------------------------------------
add_sistema_menzione("databricks", "Databricks",
    "Documenti/2. Formazione/CensimentoErogazioniFormazione.xlsx",
    "contenuto", None, "non determinabile", "Databricks (censimento erogazioni formazione)")
add_sistema_menzione("power-bi", "Power BI",
    "Documenti/2. Formazione/CensimentoErogazioniFormazione.xlsx",
    "contenuto", None, "non determinabile", "Power BI (censimento erogazioni formazione)")
add_sistema_menzione(None, "SQL",
    "Documenti/2. Formazione/CensimentoErogazioniFormazione.xlsx",
    "contenuto", None, "non determinabile", "SQL (censimento erogazioni formazione)")
add_sistema_menzione("databricks", "Databricks",
    "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/Accessi_Data_Platform_23092025.xlsx",
    "contenuto", None, "data_modifica_file (approssimata)", "Databricks (pulizia accessi workspace produzione)")
add_sistema_menzione(None, "Data Platform",
    "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/Accessi_Data_Platform_23092025.xlsx",
    "contenuto", None, "data_modifica_file (approssimata)", "Data Platform (probabile riferimento generico all'ambiente Databricks)")
add_sistema_menzione("databricks", "Databricks",
    "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/Lista_utenti_workspace_prod_23092025.xlsx",
    "contenuto", None, "data_modifica_file (approssimata)", "Databricks (lista utenti workspace produzione)")
add_sistema_menzione(None, "Workspace produzione",
    "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/Lista_utenti_workspace_prod_23092025.xlsx",
    "contenuto", None, "data_modifica_file (approssimata)", "Workspace produzione Databricks")
add_sistema_menzione("databricks", "Databricks",
    "Documenti/5. Policy e processi/Policy_Background/Pulizia_workspace_prod/utenti_attivi_prod.csv",
    "contenuto", None, "data_modifica_file (approssimata)", "Databricks (utenti attivi produzione)")
add_sistema_menzione("sap", "SAP",
    "Documenti/8. Business Glossary/Manuali_Reclami_Sharepoint/Manuale mancata registazione servizio - All.1 transazione Sap MB1B.pdf",
    "contenuto", None, "non determinabile", "SAP (manuale transazione MB1B)")
add_sistema_menzione(None, "Transazione MB1B",
    "Documenti/8. Business Glossary/Manuali_Reclami_Sharepoint/Manuale mancata registazione servizio - All.1 transazione Sap MB1B.pdf",
    "contenuto", None, "non determinabile", "Transazione SAP MB1B (mancata registrazione servizio)")
add_sistema_menzione(None, "Transazione IE03",
    "Documenti/8. Business Glossary/Manuali_Reclami_Sharepoint/Manuale mancata registazione servizio - All.1 transazione Sap MB1B.pdf",
    "contenuto", None, "non determinabile", "Transazione SAP IE03 (citata nel manuale)")

# ---------------------------------------------------------------------------
kl["meta"] = kl.get("meta", {})
kl["meta"]["nota_estensione_2026-08-04"] = (
    "Perimetro esteso il 4 agosto 2026 con i documenti dei cluster 3 (Reclami), 4 (formazione), "
    "5 (circolari organizzative + workspace) e 9 (SAL/piano Bludigit). Nuove entità e menzioni "
    "aggiunte per deduplicazione rispetto alle entità preesistenti (persone via nome_canonico, "
    "sistemi_tool via nome_canonico/abbreviazione nota). Alcune identificazioni sono inferenze "
    "esplicitamente segnalate (vedi avvisi_qualita_dati in Cronistoria): 'Aprea'->'Domenico Aprea' "
    "(cognome nelle SAL + email nel Classificatore Reclami); 'Nunziangelo Ferrulli' trattato come "
    "variante di 'Nunzio Ferrulli' già in KB; abbreviazione 'G2G'/'GOL' per GasOnLine potenzialmente "
    "in conflitto con l'entità preesistente G2G (contesto MAPPATURA DATO/ARERA, probabilmente non correlata)."
)
kl["meta"]["n_persone"] = len(kl["persone"])
kl["meta"]["n_sistemi_tool"] = len(kl["sistemi_tool"])
kl["meta"]["n_riferimenti_normativi"] = len(kl["riferimenti_normativi"])

Path(BASE / "knowledge_layer_pilota.json").write_text(json.dumps(kl, ensure_ascii=False, indent=2), encoding="utf-8")
print("persone:", len(kl["persone"]), "sistemi_tool:", len(kl["sistemi_tool"]), "riferimenti_normativi:", len(kl["riferimenti_normativi"]))
