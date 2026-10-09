import json, re, os

BASE = "/sessions/happy-sharp-lovelace/mnt/AI - Progetti/Progetti/Governance/Output/ETL_Documentale"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json")) as f:
    data = json.load(f)
with open(os.path.join(BASE, "index_ProgettoDG.json")) as f:
    idx = json.load(f)
docs = idx["documents"]

FILENAME_DATE_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")

def date_from_filename(path):
    fname = os.path.basename(path)
    m = FILENAME_DATE_RE.search(fname)
    if m:
        y, mo, d = m.groups()
        try:
            return f"{y}-{mo}-{d}"
        except Exception:
            return None
    return None

def mtime_date(path):
    meta = docs.get(path, {})
    lm = meta.get("last_modified_at")
    if lm:
        return lm[:10]
    return None

stats = {"testo": 0, "nome_file": 0, "data_modifica_file": 0, "nessuna": 0}

for path, rec in data["avanzamento"].items():
    if rec.get("data_documento"):
        rec["data_fonte"] = "testo"
        stats["testo"] += 1
        continue
    fname_date = date_from_filename(path)
    if fname_date:
        rec["data_documento"] = fname_date
        rec["data_fonte"] = "nome_file"
        stats["nome_file"] += 1
        continue
    mt = mtime_date(path)
    if mt:
        rec["data_documento"] = mt
        rec["data_fonte"] = "data_modifica_file (approssimata)"
        stats["data_modifica_file"] += 1
        continue
    rec["data_fonte"] = None
    stats["nessuna"] += 1

# contenuto: only fill the one gap, same cascade, but field is versione_data_validita
for path, rec in data["contenuto"].items():
    if rec.get("versione_data_validita"):
        continue
    fname_date = date_from_filename(path)
    if fname_date:
        rec["versione_data_validita"] = fname_date
        rec["versione_data_fonte"] = "nome_file"
        continue
    mt = mtime_date(path)
    if mt:
        rec["versione_data_validita"] = mt
        rec["versione_data_fonte"] = "data_modifica_file (approssimata)"

with open(os.path.join(BASE, "estrazione_pilota_cluster1_2.json"), "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Distribuzione fonti data (avanzamento, 23 doc):")
for k, v in stats.items():
    print(f"  {k}: {v}")
