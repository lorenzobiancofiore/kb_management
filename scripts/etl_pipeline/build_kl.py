import json, re, os, unicodedata

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    data = json.load(f)

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s

# ---------- PERSONE ----------
PAT_RESP = re.compile(r'\(Resp\.\s*([A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+){1,3})\)')
PAT_TRAIL = re.compile(r'-\s*([A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+){1,3})\s*$')
PAT_LEAD = re.compile(r'^([A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+){1,3})\s*-\s')

# esclusioni note (falsi positivi: titoli/ruoli/domini, non persone)
DENYLIST = {
    "Chief Human Resources Officer", "Comuni Serviti", "Protezione Catodica",
    "Business Unit Leaders", "Chief Financial Officer", "Referente Tecnico",
}

# token che segnalano un ruolo/organizzazione, non una persona fisica
ROLE_TOKENS = {
    "data", "owner", "steward", "team", "manager", "delegato", "amministratore",
    "organizzazione", "project", "experts", "governance", "responsabile",
    "business", "unit", "chief", "officer",
}

def looks_like_person(s):
    words = s.split()
    if not (2 <= len(words) <= 4):
        return False
    return not any(w.lower() in ROLE_TOKENS for w in words)

people = {}  # nome -> entity dict

def add_person_mention(nome, path, tipo_doc, data_doc, fonte, contesto):
    if nome in DENYLIST:
        return
    eid = slug(nome)
    if eid not in people:
        people[eid] = {"id": eid, "tipo": "persona", "nome_canonico": nome, "alias": [], "menzioni": []}
    people[eid]["menzioni"].append({
        "documento": path, "tipo_documento": tipo_doc, "data": data_doc,
        "fonte_data": fonte, "contesto": contesto,
    })

for path, r in data["avanzamento"].items():
    dd, fonte = r.get("data_documento"), r.get("data_fonte")
    for p in (r.get("partecipanti") or []):
        add_person_mention(p, path, "avanzamento", dd, fonte, "partecipante alla riunione/SAL")
    for ai in (r.get("action_item") or []):
        resp = ai.get("responsabile")
        if resp and resp != "—" and resp[0:1].isupper() and looks_like_person(resp):
            add_person_mention(resp, path, "avanzamento", dd, fonte, f"responsabile action item: {ai.get('descrizione')}")

for path, r in data["contenuto"].items():
    dd, fonte = r.get("versione_data_validita"), r.get("versione_data_fonte") or "testo"
    for ruolo in (r.get("ruoli_responsabilita") or []):
        for pat in (PAT_RESP, PAT_LEAD, PAT_TRAIL):
            m = pat.search(ruolo)
            if m:
                nome = m.group(1)
                if looks_like_person(nome):
                    add_person_mention(nome, path, "contenuto", dd, fonte, f"citato in ruoli/responsabilità: {ruolo}")
                    break

# ---------- SISTEMI / TOOL ----------
SYS_CANON = {
    "AI Academy4AI": "AI Academy4AI",
    "AI per validazione automatica e algoritmi di lettura immagini": "AI - validazione automatica letture",
    "AMPPER": "AMPPER",
    "Analytics": "Analytics Platform",
    "Analytics Platform": "Analytics Platform",
    "COPT": "COPT",
    "Cisco": "Cisco",
    "Copt per dati odorizzante": "COPT",
    "Databricks": "Databricks",
    "Databricks per piattaforma analytics": "Databricks",
    "Databricks per piattaforma analytics strutturata": "Databricks",
    "Databricks per platform analytics": "Databricks",
    "EMMG": "EMMG",
    "G2G": "G2G",
    "G4G": "G4G",
    "GIS4Road": "GIS4Road",
    "Genie": "Genie",
    "Genie e data catalog per catalogazione": "Genie",
    "Gig": "Gig",
    "LIMS": "LIMS",
    "MDM": "MDM",
    "Microsoft 365 Copilot": "Microsoft 365 Copilot",
    "PEGASO": "Pegaso",
    "Pegaso": "Pegaso",
    "Pegaso per dati di protezione catodica": "Pegaso",
    "Picarro per ricerca programmata dispersioni": "Picarro",
    "Power BI per dashboard": "Power BI",
    "Power BI per dashboard e self-BI": "Power BI",
    "PowerBI": "Power BI",
    "RTU proprietarie per IoT e acquisizione dati": "RTU",
    "SALESFORCE": "Salesforce",
    "SAP": "SAP",
    "SAP come sistema master per anagrafiche": "SAP",
    "SAP per anagrafe dati": "SAP",
    "SAP per anagrafe dati centrale": "SAP",
    "Salesforce": "Salesforce",
    "Web procat per protezione catodica": "Web Procat",
    "Databricks per ambiente centrale dati e AI, con Medallion layer operativo": "Databricks",
    "Databricks per Self-BI, dashboard e AI code": "Databricks",
    "Genie Space per analisi self-BI e query sui dati": "Genie",
    "Genie per query e report self-BI": "Genie",
    "Microsoft 365 Copilot per licenze e attivazione AI (1691 licenze, 908 Italgas Reti)": "Microsoft 365 Copilot",
    "Unity Catalog per catalogazione dati (descrizioni, tag, lineage)": "Unity Catalog",
    "Glossario, Catalogo, Ruoli, Data Quality come tool di governance configurati in piattaforma": "Suite Tool di Governance (Glossario, Catalogo, Ruoli, Data Quality)",
    "ABAC/ACL per permessi di accesso configurati e mantenuti dal Data Steward": "ABAC/ACL",
    "Databricks per formazione pratica e query SQL": "Databricks",
    "Power BI per formazione pratica e dashboard": "Power BI",
    "Genie per catalogazione e hackathon (arricchimento metadati)": "Genie",
    "Databricks per strumenti operativi e SQL base": "Databricks",
    "Power BI per dashboard": "Power BI",
    "Copilot/Genie per strumenti operativi in stanza": "Genie (con Copilot)",
    "Microsoft Entra ID per Access Management": "Microsoft Entra ID",
    "Databricks per strutturare i dati in Data Product": "Databricks",
    "Salesforce per dizionari dati esistenti": "Salesforce",
    "SAP per dizionari dati esistenti e possibile revisione delle licenze": "SAP",
    "Tibco - servizi citati come esempio di data product": "Tibco",
}

sistemi = {}
for path, r in data["contenuto"].items():
    dd, fonte = r.get("versione_data_validita"), r.get("versione_data_fonte") or "testo"
    for s in (r.get("sistemi_tool_citati") or []):
        canon = SYS_CANON.get(s, s)
        eid = slug(canon)
        if eid not in sistemi:
            sistemi[eid] = {"id": eid, "tipo": "sistema_tool", "nome_canonico": canon, "alias": [], "menzioni": []}
        if s != canon and s not in sistemi[eid]["alias"]:
            sistemi[eid]["alias"].append(s)
        sistemi[eid]["menzioni"].append({
            "documento": path, "tipo_documento": "contenuto", "data": dd,
            "fonte_data": fonte, "contesto": s,
        })

# ---------- RIFERIMENTI NORMATIVI (raggruppati per famiglia, non fusi) ----------
FAMIGLIE = [
    ("ARERA", re.compile(r"ARERA")),
    ("Privacy", re.compile(r"privacy|DPO", re.I)),
    ("Antitrust / Anticorruzione", re.compile(r"antitrust|corruzione|231", re.I)),
    ("Salute e Sicurezza", re.compile(r"sicurezza.*lavor|81/08|salute", re.I)),
    ("Ambientale / Impianti", re.compile(r"ambiental|atex|dpr 462|cpi|gas naturale|gpl|distribuzione gas", re.I)),
    ("Sicurezza informatica (NIS/CER)", re.compile(r"NIS|CER", re.I)),
    ("Etica / Compliance generale", re.compile(r"etic|compliance", re.I)),
]

normative = {}
for path, r in data["contenuto"].items():
    dd, fonte = r.get("versione_data_validita"), r.get("versione_data_fonte") or "testo"
    for n in (r.get("riferimenti_normativi") or []):
        famiglia = next((fam for fam, pat in FAMIGLIE if pat.search(n)), "Altro")
        eid = slug(n)
        if eid not in normative:
            normative[eid] = {"id": eid, "tipo": "riferimento_normativo", "nome_canonico": n,
                               "famiglia": famiglia, "menzioni": []}
        normative[eid]["menzioni"].append({
            "documento": path, "tipo_documento": "contenuto", "data": dd,
            "fonte_data": fonte, "contesto": n,
        })

entities = {
    "persone": sorted(people.values(), key=lambda e: e["nome_canonico"]),
    "sistemi_tool": sorted(sistemi.values(), key=lambda e: e["nome_canonico"]),
    "riferimenti_normativi": sorted(normative.values(), key=lambda e: (e["famiglia"], e["nome_canonico"])),
}

with open(os.path.join(BASE, "knowledge_layer_pilota.json"), "w") as f:
    json.dump(entities, f, ensure_ascii=False, indent=2)

print("Persone:", len(entities["persone"]))
print("Sistemi/tool (canonici):", len(entities["sistemi_tool"]))
print("Riferimenti normativi (voci):", len(entities["riferimenti_normativi"]))
