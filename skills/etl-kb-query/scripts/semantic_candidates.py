#!/usr/bin/env python3
"""
Fallback lessicale (TF-IDF) su Estrazione — Passo 3bis di etl-kb-query.
========================================================================

A cosa serve: quando una domanda non trova candidati convincenti tramite
match esatto/per-alias in Catalogo e Knowledge Layer (Passo 2/3), il tema
potrebbe comunque essere descritto nei documenti con parole diverse da
quelle usate in `label`/`nome_canonico`/`alias` — quei campi coprono bene
le entità nominate esplicitamente, non i temi descritti solo nel testo
libero di Estrazione. Questo script costruisce una rappresentazione TF-IDF
dei campi testuali liberi di `estrazione_*.json` e ritorna i documenti più
simili (coseno) a una query in linguaggio naturale.

È un fallback lessicale, non un motore semantico vero: usalo per allargare
l'elenco di documenti candidati da verificare al Passo 4a, non come fonte
diretta di un fatto — la similarità testuale suggerisce dove guardare, non
conferma un contenuto.

Implementazione TF-IDF (tokenizzazione, stopword IT/EN + rumore di corpus
aziendale, TF-IDF con filtro min_df/max_df, normalizzazione L2) volutamente
nello stesso stile minimale-solo-numpy usato in Fase 2 (`catalogazione.py`)
per coerenza tra le fasi della pipeline — nessuna dipendenza da scikit-learn.

Uso:
    python3 semantic_candidates.py --etl-dir "<path/Output/ETL_Documentale>" \
        --query "firma elettronica documenti contrattuali" [--top 10]

Output: JSON su stdout, elenco di candidati ordinati per punteggio
decrescente:
    [
      {"documento": "percorso/relativo/Doc.pptx", "tipo": "avanzamento",
       "score": 0.421, "estratto": "argomento o prime decisioni..."},
      ...
    ]
"""
import argparse
import glob
import json
import math
import os
import re
import sys
from collections import Counter

import numpy as np

# ---------------------------------------------------------------------------
# Stopword e tokenizzazione — stesso set/stile di catalogazione.py (Fase 2),
# per coerenza di comportamento lessicale tra le fasi della pipeline.
# ---------------------------------------------------------------------------

STOPWORDS_IT = set("""
a ad al alla alle agli allo agli anche ancora avere avevo aveva avevano
avuto ben che chi ci come con contro cui da dai dal dalla dalle dallo degli
dei del della delle dello di dice dietro dopo dove due e ecco ed egli ella
essere essi fa faccio fare farò fino fra gia già gli ha hai hanno ho i il
in invece io la le lei li lo loro lui ma mi mio mia miei mie ne negli nei
nel nella nelle nello no noi non nostra nostre nostri nostro nuovo o oppure
ora per perche perché però più poi possono potrebbe pochi quale quali quando
quanto quasi quella quelle quelli quello questa queste questi questo qui
quindi se sei senza si sia siamo siano siete sono sopra sotto sta stai
stanno stata state stati stato stessa stesse stessi stesso su sua subito
sue sugli sui sul sulla sulle sullo suo suoi tra tre tua tue tuo tuoi tutta
tutte tutti tutto un una uno va vai vengono venuto verso vi via voi vostra
vostre vostri vostro
""".split())

STOPWORDS_EN = set("""
the a an of and or to in on for with is are was were be been being this
that these those as at by from it its into not no yes we you your our
""".split())

STOPWORDS_NOISE = set("""
slide pag pagina pag. http https www com pptx docx xlsx pdf doc rtf csv
gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre
novembre dicembre lunedi martedi mercoledi giovedi venerdi sabato domenica
""".split())

STOPWORDS = STOPWORDS_IT | STOPWORDS_EN | STOPWORDS_NOISE

TOKEN_RE = re.compile(r"[a-zàèéìòù]{3,}", re.IGNORECASE)


def tokenize(text):
    if not text:
        return []
    text = text.lower()
    tokens = TOKEN_RE.findall(text)
    return [t for t in tokens if t not in STOPWORDS and not t.isdigit()]


# ---------------------------------------------------------------------------
# TF-IDF minimale (solo numpy) — stessa implementazione di catalogazione.py
# ---------------------------------------------------------------------------

def build_tfidf(token_lists, min_df=1, max_df=0.85):
    """TF-IDF con filtro su termini iper-rari (min_df) e iper-comuni
    (max_df, come frazione dei documenti). min_df=1 di default qui perché
    il corpus di una singola query è tipicamente piccolo (decine-centinaia
    di documenti Estrazione, non migliaia)."""
    n_docs = len(token_lists)
    doc_freq = Counter()
    for tokens in token_lists:
        doc_freq.update(set(tokens))

    max_df_count = max(min_df, math.ceil(max_df * n_docs)) if max_df is not None else n_docs
    vocab = [w for w, df in doc_freq.items() if min_df <= df <= max_df_count]
    if not vocab:
        vocab = [w for w, df in doc_freq.items() if df >= min_df]
    vocab_index = {w: i for i, w in enumerate(vocab)}
    idf = np.zeros(len(vocab))
    for w, i in vocab_index.items():
        idf[i] = math.log((1 + n_docs) / (1 + doc_freq[w])) + 1.0

    matrix = np.zeros((n_docs, len(vocab)), dtype=np.float32)
    for row, tokens in enumerate(token_lists):
        if not tokens:
            continue
        counts = Counter(tokens)
        total = len(tokens)
        for w, c in counts.items():
            idx = vocab_index.get(w)
            if idx is not None:
                matrix[row, idx] = (c / total) * idf[idx]

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    return matrix, vocab


# ---------------------------------------------------------------------------
# Caricamento Estrazione e costruzione del corpus testuale per documento
# ---------------------------------------------------------------------------

def pick_file(etl_dir, patterns):
    for pat in patterns:
        matches = sorted(
            f for f in glob.glob(os.path.join(etl_dir, pat))
            if ".bak" not in os.path.basename(f)
        )
        if matches:
            return max(matches, key=os.path.getmtime)
    return None


def as_text(value):
    """Appiattisce liste/dict/stringhe annidate (es. action_item con dict)
    in un'unica stringa, per non escludere campi non puramente testuali."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(as_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(as_text(v) for v in value.values())
    return str(value)


# Campi liberi rilevanti per similarità testuale, per tipo di documento.
# Deliberatamente esclude campi puramente strutturali (date, path, fonte).
FIELDS_AVANZAMENTO = [
    "contenuti_trattati", "decisioni", "rischi_blocchi", "prossimi_passi",
    "action_item", "parole_chiave",
]
FIELDS_CONTENUTO = [
    "argomento", "processi_attivita", "ruoli_responsabilita",
    "sistemi_tool_citati", "riferimenti_normativi", "parole_chiave",
]


def load_corpus(estrazione):
    """Ritorna lista di (doc_path, tipo, testo_completo, estratto_breve)."""
    corpus = []
    if not estrazione or not isinstance(estrazione, dict):
        return corpus

    for doc_path, entry in (estrazione.get("avanzamento") or {}).items():
        parts = [as_text(entry.get(f)) for f in FIELDS_AVANZAMENTO]
        testo = " ".join(p for p in parts if p)
        estratto = as_text(entry.get("decisioni")) or as_text(entry.get("contenuti_trattati"))
        corpus.append((doc_path, "avanzamento", testo, estratto[:280]))

    for doc_path, entry in (estrazione.get("contenuto") or {}).items():
        parts = [as_text(entry.get(f)) for f in FIELDS_CONTENUTO]
        testo = " ".join(p for p in parts if p)
        estratto = as_text(entry.get("argomento"))
        corpus.append((doc_path, "contenuto", testo, estratto[:280]))

    return corpus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etl-dir", required=True, help="Path a Output/ETL_Documentale")
    ap.add_argument("--query", required=True, help="Domanda o parole chiave (incluse le varianti del Passo 1)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--min-score", type=float, default=0.03,
                     help="Soglia minima di similarità coseno per essere incluso nel risultato")
    args = ap.parse_args()

    estrazione_path = pick_file(args.etl_dir, ["estrazione_*.json"])
    if not estrazione_path:
        print(json.dumps({"errore": "nessun file estrazione_*.json trovato in " + args.etl_dir}, ensure_ascii=False))
        sys.exit(1)

    with open(estrazione_path, encoding="utf-8") as f:
        estrazione = json.load(f)

    corpus = load_corpus(estrazione)
    if not corpus:
        print(json.dumps({"errore": "estrazione vuota o senza campi testuali utilizzabili"}, ensure_ascii=False))
        sys.exit(1)

    token_lists = [tokenize(testo) for _, _, testo, _ in corpus]
    query_tokens = tokenize(args.query)

    # La query è trattata come un documento aggiuntivo del corpus, così il
    # suo TF-IDF usa lo stesso vocabolario/idf dei documenti reali.
    matrix, vocab = build_tfidf(token_lists + [query_tokens])
    query_vec = matrix[-1]
    doc_matrix = matrix[:-1]

    # Cosine similarity: righe già L2-normalizzate da build_tfidf, quindi
    # il dot product è direttamente il coseno.
    scores = doc_matrix @ query_vec

    ranked = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    results = []
    for i in ranked[: args.top]:
        score = float(scores[i])
        if score < args.min_score:
            break
        doc_path, tipo, _, estratto = corpus[i]
        results.append({
            "documento": doc_path,
            "tipo": tipo,
            "score": round(score, 4),
            "estratto": estratto,
        })

    print(json.dumps({
        "estrazione_file": estrazione_path,
        "query": args.query,
        "n_documenti_corpus": len(corpus),
        "risultati": results,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
