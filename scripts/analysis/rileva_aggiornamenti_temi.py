#!/usr/bin/env python3
"""
Rileva aggiornamenti non incorporati sui temi tracciati in Cronistoria.

Passo derivato (non una fase), generico e riutilizzabile su qualunque
progetto che segua la pipeline ETL documentale a 5 fasi. Lavora sopra
`possibili_aggiornamenti_decisioni` della Cronistoria (Fase 5) e su
Estrazione (Fase 3): per ogni tema già tracciato manualmente da un umano,
verifica se esistono documenti più recenti di quelli già incorporati nella
catena "decisione_precedente -> decisione_successiva -> eseguita_in" che
menzionano le stesse parole chiave del tema, e segnala il potenziale
aggiornamento non ancora incorporato come avviso di qualità dati.

Deliberatamente NON risolve l'aggiornamento in automatico (non riscrive la
catena né decide se il documento trovato È davvero un aggiornamento della
decisione) - questo resta un giudizio editoriale umano, coerente con il
principio già in uso su questo progetto per cui il livello
"possibili_aggiornamenti_decisioni" è INTERPRETATO e curato, non mecanico.
Lo script si limita a un compito mecanico e verificabile: "esiste un
documento più recente che tocca lo stesso tema e non risulta ancora nella
catena?" - la risposta a "è davvero un aggiornamento" resta a chi legge
l'avviso.

Due modalità:

1. --suggest-keywords: per ogni tema di possibili_aggiornamenti_decisioni
   che non ha ancora un campo "parole_chiave", propone candidati estraendo
   frasi/parole significative dal testo già presente nel tema
   (decisione_precedente, decisione_successiva, eseguita_in). Non modifica
   alcun file: stampa le proposte a schermo/report perché un umano le
   confermi o corregga prima di salvarle a mano nel campo "parole_chiave"
   del tema, dentro il file Cronistoria.

2. Modalità di rilevazione (default, richiede che i temi abbiano già
   "parole_chiave" confermate): per ogni tema con parole_chiave, scansiona
   tutti i documenti di Estrazione (campi testuali rilevanti secondo lo
   schema avanzamento/contenuto) e individua quelli che contengono almeno
   una parola chiave del tema con una data comparabile (YYYY-MM-DD) più
   recente della data più recente già presente nella catena del tema. Per
   ogni documento trovato non ancora segnalato, aggiunge una voce in
   avvisi_qualita_dati (rispettando lo schema già in uso nel file) con tipo
   "possibile_aggiornamento_tema_non_incorporato".

Uso:
    # Passo 1: proponi parole chiave per i temi che non le hanno ancora
    python3 rileva_aggiornamenti_temi.py --cronistoria cronistoria.json --suggest-keywords

    # Passo 2 (dopo aver confermato/scritto a mano le parole chiave nel tema
    # dentro cronistoria.json):
    python3 rileva_aggiornamenti_temi.py --cronistoria cronistoria.json \
        --estrazione estrazione.json --output cronistoria.json --report report.md
"""
import argparse
import json
import re
from collections import Counter


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_iso_date(d):
    return bool(d) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d)))


TESTO_FIELDS_CONTENUTO = ["argomento", "processi_attivita", "ruoli_responsabilita",
                          "sistemi_tool_citati", "riferimenti_normativi"]
TESTO_FIELDS_AVANZAMENTO = ["contenuti_trattati", "decisioni", "rischi_blocchi",
                            "prossimi_passi", "action_item"]


def doc_text_blobs(doc_data, tipo_documento):
    """Ritorna la lista di stringhe testuali rilevanti di un documento di
    Estrazione, a seconda che sia avanzamento o contenuto. Gli action_item
    sono dict, vengono normalizzati a stringa."""
    fields = TESTO_FIELDS_AVANZAMENTO if tipo_documento == "avanzamento" else TESTO_FIELDS_CONTENUTO
    blobs = []
    for campo in fields:
        val = doc_data.get(campo)
        if not val:
            continue
        if isinstance(val, str):
            blobs.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    blobs.append(item)
                elif isinstance(item, dict):
                    blobs.append(" ".join(str(v) for v in item.values() if isinstance(v, str)))
    return blobs


def doc_date(doc_data, tipo_documento):
    if tipo_documento == "avanzamento":
        return doc_data.get("data_documento")
    return doc_data.get("versione_data_validita")


# ---------- Modalità 1: suggerimento parole chiave ----------

STOPWORDS_IT = set("""
di a da in con su per tra fra il lo la i gli le un uno una del dello della
dei degli delle al allo alla ai agli alle e o ma se che non più anche
come già ancora quando dove chi cui questo questa questi queste quello
quella quelli quelle suo sua suoi sue loro nel nella nei nelle sono stato
stata stati state essere avere fare tutto tutti tutta tutte
""".split())


def estrai_candidati_parole_chiave(testi, top_n=8):
    """Estrae frasi/parole candidate come parole chiave da una lista di testi
    (tipicamente decisione_precedente/successiva/eseguita_in di un tema).
    Euristica semplice, senza librerie NLP (coerente con la leggerezza già
    in uso nel resto della pipeline): sequenze di 1-3 parole capitalizzate
    (probabili nomi propri/termini tecnici) più le parole più frequenti al
    netto delle stopword italiane."""
    frasi_capitalizzate = Counter()
    parole_frequenti = Counter()
    for testo in testi:
        if not testo:
            continue
        for m in re.finditer(r"\b([A-ZÀ-Ù][a-zà-ù]+(?:\s+[A-ZÀ-Ù][a-zà-ù]+){0,2})\b", testo):
            frasi_capitalizzate[m.group(1)] += 1
        for parola in re.findall(r"[A-Za-zà-ùÀ-Ù]{4,}", testo.lower()):
            if parola not in STOPWORDS_IT:
                parole_frequenti[parola] += 1
    candidati = [f for f, _ in frasi_capitalizzate.most_common(top_n)]
    for p, _ in parole_frequenti.most_common(top_n):
        if not any(p in c.lower() for c in candidati):
            candidati.append(p)
    return candidati[:top_n]


def suggerisci_parole_chiave(cronistoria):
    temi = cronistoria.get("possibili_aggiornamenti_decisioni", [])
    proposte = []
    for tema in temi:
        if tema.get("parole_chiave"):
            continue
        testi = []
        for chiave in ("decisione_precedente", "decisione_successiva", "eseguita_in"):
            blocco = tema.get(chiave)
            if blocco and blocco.get("testo"):
                testi.append(blocco["testo"])
        testi.append(tema.get("tema", ""))
        candidati = estrai_candidati_parole_chiave(testi)
        proposte.append({"tema": tema.get("tema"), "candidati": candidati})
    return proposte


# ---------- Modalità 2: rilevazione documenti più recenti ----------

def ultima_data_comparabile_tema(tema):
    date_iso = []
    for chiave in ("decisione_precedente", "decisione_successiva", "eseguita_in"):
        blocco = tema.get(chiave)
        if blocco and is_iso_date(blocco.get("data")):
            date_iso.append(blocco["data"])
    return max(date_iso) if date_iso else None


def documenti_gia_segnalati(cronistoria, tipo_avviso):
    """Set di (tema, documento) già presenti come avviso di questo tipo, per
    evitare di duplicare la segnalazione ad ogni esecuzione successiva."""
    esistenti = set()
    for avviso in cronistoria.get("avvisi_qualita_dati", []):
        if avviso.get("tipo") != tipo_avviso:
            continue
        tema = avviso.get("tema")
        for doc in avviso.get("documenti_coinvolti", avviso.get("documenti", [])):
            esistenti.add((tema, doc))
    return esistenti


def append_avviso(cronistoria, tipo, descrizione, documenti, tema=None):
    """Rispetta lo schema già in uso nel file: se le voci esistenti hanno
    'tipo'/'documenti_coinvolti' usa quello, altrimenti il più semplice
    'descrizione'/'documenti' (stessa logica già in uso per B4 di
    etl-kb-build, qui con l'aggiunta del campo 'tema' per poter risalire
    al tema tracciato senza doverlo re-interpretare dal testo)."""
    voci = cronistoria.setdefault("avvisi_qualita_dati", [])
    usa_tipo = any("tipo" in v for v in voci) or tipo is not None
    if usa_tipo:
        voce = {"tipo": tipo, "descrizione": descrizione, "documenti_coinvolti": documenti}
    else:
        voce = {"descrizione": descrizione, "documenti": documenti}
    if tema:
        voce["tema"] = tema
    voci.append(voce)


def rileva_aggiornamenti(cronistoria, estrazione, tipo_avviso="possibile_aggiornamento_tema_non_incorporato"):
    temi = cronistoria.get("possibili_aggiornamenti_decisioni", [])
    temi_con_chiavi = [t for t in temi if t.get("parole_chiave")]
    if not temi_con_chiavi:
        return 0
    gia_segnalati = documenti_gia_segnalati(cronistoria, tipo_avviso)
    n_nuovi = 0
    for tema in temi_con_chiavi:
        parole = [p.lower() for p in tema["parole_chiave"]]
        ultima_data = ultima_data_comparabile_tema(tema)
        for sezione in ("avanzamento", "contenuto"):
            for doc, dati in estrazione.get(sezione, {}).items():
                if (tema.get("tema"), doc) in gia_segnalati:
                    continue
                blobs = doc_text_blobs(dati, sezione)
                testo_completo = " ".join(blobs).lower()
                if not any(p in testo_completo for p in parole):
                    continue
                data_doc = doc_date(dati, sezione)
                if not is_iso_date(data_doc):
                    continue  # data non comparabile: non possiamo dire se è "più recente", da controllare a mano
                if ultima_data and data_doc <= ultima_data:
                    continue  # non più recente della catena già nota
                append_avviso(
                    cronistoria,
                    tipo=tipo_avviso,
                    descrizione=(f"Il documento '{doc}' (data {data_doc}) menziona parole chiave del "
                                 f"tema '{tema.get('tema')}' ed è più recente dell'ultima voce nota nella "
                                 f"catena di possibili_aggiornamenti_decisioni ({ultima_data}). "
                                 f"Potrebbe contenere un aggiornamento non ancora incorporato: da "
                                 f"verificare a mano, non incorporato automaticamente."),
                    documenti=[doc],
                    tema=tema.get("tema"),
                )
                gia_segnalati.add((tema.get("tema"), doc))
                n_nuovi += 1
    return n_nuovi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cronistoria", required=True)
    ap.add_argument("--estrazione")
    ap.add_argument("--output", help="Dove scrivere la Cronistoria aggiornata (default: sovrascrive --cronistoria)")
    ap.add_argument("--report")
    ap.add_argument("--suggest-keywords", action="store_true",
                     help="Non modifica nulla: propone parole chiave candidate per i temi che non le hanno ancora")
    args = ap.parse_args()

    cronistoria = load_json(args.cronistoria)

    if args.suggest_keywords:
        proposte = suggerisci_parole_chiave(cronistoria)
        if not proposte:
            print("Tutti i temi tracciati hanno già parole_chiave (o non ci sono temi).")
            return
        print(f"Proposte di parole chiave per {len(proposte)} tema/i senza parole_chiave "
              f"(da confermare/correggere a mano prima di salvarle nel campo 'parole_chiave' del tema):\n")
        for p in proposte:
            print(f"- Tema: {p['tema']}")
            print(f"  Candidati: {', '.join(p['candidati'])}\n")
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write("# Proposte parole chiave per temi tracciati\n\n")
                for p in proposte:
                    f.write(f"## {p['tema']}\n\nCandidati: {', '.join(p['candidati'])}\n\n")
            print(f"Scritto anche: {args.report}")
        return

    if not args.estrazione:
        ap.error("--estrazione è richiesto in modalità di rilevazione (senza --suggest-keywords)")

    estrazione = load_json(args.estrazione)
    n_nuovi = rileva_aggiornamenti(cronistoria, estrazione)

    output_path = args.output or args.cronistoria
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cronistoria, f, ensure_ascii=False, indent=2)
    print(f"Scritto: {output_path}")
    print(f"Nuovi avvisi 'possibile_aggiornamento_tema_non_incorporato': {n_nuovi}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("# Rilevazione aggiornamenti non incorporati sui temi tracciati\n\n")
            f.write(f"Nuovi avvisi generati in questa esecuzione: {n_nuovi}\n\n")
            for avviso in cronistoria.get("avvisi_qualita_dati", []):
                if avviso.get("tipo") == "possibile_aggiornamento_tema_non_incorporato":
                    f.write(f"- **{avviso.get('tema')}**: {avviso.get('descrizione')}\n")
        print(f"Scritto anche: {args.report}")


if __name__ == "__main__":
    main()
