#!/usr/bin/env python3
"""
Rilevamento delle informazioni discordanti nella knowledge base ETL.

Il confronto avviene SOLO tra documenti dello stesso cluster del catalogo.
Lo script non giudica: prepara i dossier per cluster (passo `prepara`), poi un
agente (Claude) li legge e scrive per ogni cluster un file `risultati_<id>.json`;
il passo `unisci` valida quei file e aggiorna `discordanze_pilota.json`,
conservando le conferme già date dall'utente.

Passi:
  prepara  --etl-dir <KB> --out-dir <scratch> [--da-percorsi <file.json>|--cluster 1,2]
           Scrive <out>/dossier_<cid>.json per i cluster con almeno 2 documenti estratti.
           --da-percorsi: lista JSON di percorsi relativi (nuovi/modificati); si
           preparano solo i cluster che li contengono (rilevamento incrementale).
  unisci   --etl-dir <KB> --in-dir <scratch> [--cluster-elaborati 1,2,...]
           Valida i risultati_<id>.json e aggiorna <KB>/discordanze_pilota.json.
           Per i cluster elaborati le discordanze senza conferma che non vengono
           riproposte passano a `rientrata`; quelle confermate restano.

Natura (campo `natura`): "contraddizione" (documenti validi nello stesso momento che si
contraddicono: richiede la conferma dell'utente) oppure "evoluzione" (il documento successivo
aggiorna il precedente: non si chiede conferma, finisce nella cronistoria come catena
`evoluzioni_rilevate`, con stato `evoluzione`). Se l'agente non la indica si deriva: tutte le
affermazioni con data ISO e date distinte = evoluzione; altrimenti contraddizione.

Schema di una discordanza (output dell'agente, per cluster):
  {"cluster": "1", "discordanze": [{
      "tema": "breve titolo",
      "categoria": "ruolo|responsabile|data|nome|decisione|sistema|altro",
      "motivo": "perché le versioni sono incompatibili",
      "affermazioni": [{"documento": "<percorso>", "data": "YYYY-MM-DD|null", "testo": "..."}],
      "proposta": {"documento": "<percorso della versione proposta come valida>", "motivazione": "..."}}]}

Stato (campo `stato`): aperta | confermata | rientrata | evoluzione.
Una discordanza confermata porta il campo `conferma` {esito, documento, testo, data, fonte}.
L'id è stabile: "dc-" + sha1(cluster|tema normalizzato|documenti ordinati)[:10].
"""
import argparse
import glob
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone


def nfc(s):
    return unicodedata.normalize("NFC", s)


def norm(s):
    return re.sub(r"\s+", " ", nfc(str(s)).strip().lower())


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pick(etl, pat):
    return (sorted(f for f in glob.glob(os.path.join(etl, pat)) if ".bak" not in f) or [None])[-1]


def disc_id(cluster, tema, docs):
    base = "|".join([str(cluster), norm(tema)[:60]] + sorted(nfc(d) for d in docs))
    return "dc-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]


def doc_date(t, r):
    return r.get("data_documento") if t == "avanzamento" else r.get("versione_data_validita")


def cluster_docs(cat, est):
    """cluster_id -> [(percorso come in estrazione, tipo, record)] dei documenti estratti."""
    ex = {}
    for t in ("avanzamento", "contenuto"):
        for p, r in est.get(t, {}).items():
            ex[nfc(p)] = (p, t, r)
    out = {}
    for p, d in cat["documents"].items():
        if nfc(p) in ex:
            out.setdefault(str(d["cluster_id"]), []).append(ex[nfc(p)])
    return out


def prepara(a):
    cat = load(pick(a.etl_dir, "catalogo_*.json"))
    est = load(pick(a.etl_dir, "estrazione_*.json"))
    esist = load(os.path.join(a.etl_dir, "discordanze_pilota.json"), {"discordanze": []})
    per = cluster_docs(cat, est)
    scelti = None
    if a.cluster:
        scelti = set(a.cluster.split(","))
    elif a.da_percorsi:
        toccati = {nfc(p) for p in load(a.da_percorsi, [])}
        scelti = {str(d["cluster_id"]) for p, d in cat["documents"].items() if nfc(p) in toccati}
    os.makedirs(a.out_dir, exist_ok=True)
    n = 0
    for cid, docs in sorted(per.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
        if len(docs) < 2 or (scelti is not None and cid not in scelti):
            continue
        docs.sort(key=lambda x: str(doc_date(x[1], x[2]) or "9999"))
        dossier = {
            "cluster": cid,
            "label": cat["clusters"][cid].get("label", ""),
            "documenti": [{"percorso": p, "tipo": t, "data": doc_date(t, r),
                           "data_fonte": r.get("data_fonte") or r.get("versione_data_fonte"), "scheda": r}
                          for p, t, r in docs],
            "discordanze_gia_note": [{k: d.get(k) for k in ("id", "tema", "stato")} for d in esist.get("discordanze", [])
                                     if str(d.get("cluster")) == cid],
        }
        with open(os.path.join(a.out_dir, "dossier_%s.json" % cid), "w", encoding="utf-8") as f:
            json.dump(dossier, f, ensure_ascii=False, indent=1)
        n += 1
    print("dossier scritti:", n, "in", a.out_dir)


def natura_di(item):
    n = str(item.get("natura") or "").strip().lower()
    if n in ("evoluzione", "contraddizione"):
        return n
    ds = [x.get("data") for x in item.get("affermazioni", [])]
    iso = [bool(d and re.match(r"^\d{4}-\d{2}-\d{2}$", str(d))) for d in ds]
    return "evoluzione" if all(iso) and len(set(ds)) == len(ds) else "contraddizione"


def valida(item, cid, ammessi):
    errs = []
    for k in ("tema", "motivo"):
        if not str(item.get(k) or "").strip():
            errs.append("manca " + k)
    aff = item.get("affermazioni") or []
    if len(aff) < 2:
        errs.append("servono almeno 2 affermazioni")
    docs = []
    for x in aff:
        d = nfc(x.get("documento") or "")
        if d not in ammessi:
            errs.append("documento non del cluster %s: %s" % (cid, x.get("documento")))
        docs.append(d)
        if not str(x.get("testo") or "").strip():
            errs.append("affermazione senza testo")
    if len(set(docs)) < 2:
        errs.append("le affermazioni devono provenire da almeno 2 documenti diversi")
    pr = item.get("proposta") or {}
    if nfc(pr.get("documento") or "") not in {d for d in docs}:
        errs.append("la proposta deve indicare uno dei documenti in conflitto")
    return errs


def scrivi_evoluzioni(etl, lista):
    """Porta le evoluzioni in cronistoria_*.json come `evoluzioni_rilevate` (non tocca le catene curate)."""
    cp = pick(etl, "cronistoria_*.json")
    cr = load(cp)
    if cr is None:
        return
    ev = []
    for d in lista:
        if d.get("stato") != "evoluzione":
            continue
        passi = sorted(d["affermazioni"], key=lambda x: str(x.get("data") or "9999"))
        ev.append({"id": d["id"], "cluster": d["cluster"], "tema": d["tema"], "categoria": d.get("categoria"),
                   "passi": [{"documento": x["documento"], "data": x.get("data"), "testo": x["testo"]} for x in passi],
                   "versione_valida": passi[-1]["documento"], "nota": d.get("motivo", "")})
    cr["evoluzioni_rilevate"] = ev
    with open(cp, "w", encoding="utf-8") as f:
        json.dump(cr, f, ensure_ascii=False, indent=1)


def unisci(a):
    cat = load(pick(a.etl_dir, "catalogo_*.json"))
    est = load(pick(a.etl_dir, "estrazione_*.json"))
    per = cluster_docs(cat, est)
    path = os.path.join(a.etl_dir, "discordanze_pilota.json")
    cur = load(path, {"meta": {}, "discordanze": []})
    vecchie = {d["id"]: d for d in cur.get("discordanze", [])}
    nuove, scartate, elaborati = {}, [], set(a.cluster_elaborati.split(",")) if a.cluster_elaborati else set()
    for f in sorted(glob.glob(os.path.join(a.in_dir, "risultati_*.json"))):
        r = load(f, {})
        cid = str(r.get("cluster"))
        elaborati.add(cid)
        ammessi = {nfc(p) for p, _, _ in per.get(cid, [])}
        date = {nfc(p): doc_date(t, rec) for p, t, rec in per.get(cid, [])}
        for it in r.get("discordanze", []):
            errs = valida(it, cid, ammessi)
            if errs:
                scartate.append({"cluster": cid, "tema": it.get("tema"), "errori": errs})
                continue
            docs = [x["documento"] for x in it["affermazioni"]]
            did = disc_id(cid, it["tema"], docs)
            for x in it["affermazioni"]:
                if not x.get("data"):
                    x["data"] = date.get(nfc(x["documento"]))
            d = {"id": did, "cluster": cid, "cluster_label": cat["clusters"][cid].get("label", ""),
                 "tema": it["tema"].strip(), "categoria": it.get("categoria") or "altro",
                 "motivo": it["motivo"].strip(), "affermazioni": it["affermazioni"],
                 "proposta": it["proposta"], "stato": "aperta", "natura": natura_di(it),
                 "rilevata_il": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if d["natura"] == "evoluzione":
                d["stato"] = "evoluzione"
            if did in vecchie:
                v = vecchie[did]
                d["rilevata_il"] = v.get("rilevata_il", d["rilevata_il"])
                if v.get("conferma"):
                    d["stato"], d["conferma"] = "confermata", v["conferma"]
            nuove[did] = d
    for v in vecchie.values():  # discordanze create prima del campo natura
        v.setdefault("natura", natura_di(v))
        if v["natura"] == "evoluzione" and v.get("stato") == "aperta":
            v["stato"] = "evoluzione"
    out = {}
    for did, v in vecchie.items():
        if did in nuove:
            continue
        if str(v.get("cluster")) in elaborati and v.get("stato") != "confermata":
            v = dict(v, stato="rientrata")  # non più riproposta dall'ultimo confronto
        out[did] = v
    out.update(nuove)
    lista = sorted(out.values(), key=lambda d: (d["stato"] != "aperta", int(d["cluster"]) if str(d["cluster"]).isdigit() else 999, d["id"]))
    meta = {"aggiornato_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cluster_confrontati_ultima_passata": sorted(elaborati, key=lambda x: int(x) if x.isdigit() else 999),
            "regola": "confronto solo tra documenti dello stesso cluster; default: prevale il più recente, segnato non confermato",
            "evoluzioni": sum(1 for d in lista if d["stato"] == "evoluzione"),
            "aperte": sum(1 for d in lista if d["stato"] == "aperta"),
            "confermate": sum(1 for d in lista if d["stato"] == "confermata"),
            "rientrate": sum(1 for d in lista if d["stato"] == "rientrata"),
            "scartate_in_validazione": len(scartate)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "discordanze": lista}, f, ensure_ascii=False, indent=1)
    scrivi_evoluzioni(a.etl_dir, lista)
    print(json.dumps(meta, ensure_ascii=False))
    for s in scartate:
        print("SCARTATA", s)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepara")
    p.add_argument("--etl-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--da-percorsi")
    p.add_argument("--cluster")
    p.set_defaults(fn=prepara)
    u = sp.add_parser("unisci")
    u.add_argument("--etl-dir", required=True)
    u.add_argument("--in-dir", required=True)
    u.add_argument("--cluster-elaborati")
    u.set_defaults(fn=unisci)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
