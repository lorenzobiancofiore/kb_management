#!/usr/bin/env python3
"""
Fase 2 - Catalogazione
========================
Flusso ETL Documentale (Governance / Challenge 1 - Knowledge & Governance)

Cosa fa questo script:
- Parte dall'indice prodotto dalla Fase 1 (indicizzazione).
- Per ogni documento leggibile, estrae il testo (pptx, docx, xlsx, pdf, csv,
  md, html, txt, sql). Per i formati non supportati o in caso di errore di
  estrazione, usa come segnale debole nome file + percorso e marca il
  documento come "solo_metadata".
- Costruisce una rappresentazione TF-IDF di ogni documento e clusterizza i
  documenti per similarità di contenuto (clustering agglomerativo con
  average-linkage, implementato senza dipendenze esterne oltre numpy).
- Il numero di cluster è deciso dai dati: il merge si ferma automaticamente
  al "salto" più grande nella sequenza delle similarità di merge (metodo
  del maggior gap sul dendrogramma), entro un range di cluster plausibile.
- Per ogni cluster genera un'etichetta automatica (le parole più
  caratterizzanti) e i documenti più rappresentativi, da validare o
  rinominare.
- Scrive un catalogo (catalogo.json) con, per ogni documento, il cluster
  assegnato — così le fasi successive (estrazione, knowledge layer) possono
  concentrarsi sui documenti di uno stesso cluster.

Due modalità:
- BATCH (default): riclusterizza tutto da zero. Usarla per la prima
  catalogazione o per un refresh periodico completo.
    python3 catalogazione.py --index index_ProgettoDG.json --root "/percorso/Progetto DG" \
        --output catalogo.json --report catalogo_report.md [--label-prefix "Data Governance - "]

- INCREMENTALE (--catalog-in): parte da un catalogo già esistente e valuta
  solo i documenti nuovi o con contenuto cambiato rispetto a quel catalogo
  (via content_hash). Ogni documento nuovo/cambiato viene confrontato con
  il centroide di ciascun cluster esistente: se la similarità supera
  --assign-threshold (default 0.15) viene assegnato lì SENZA toccare
  l'etichetta del cluster (che resta quella eventualmente già validata a
  mano); altrimenti finisce in uno o più cluster nuovi, creati solo con i
  documenti "non assegnabili" di questo giro.
    python3 catalogazione.py --index index_ProgettoDG.json --root "/percorso/Progetto DG" \
        --catalog-in catalogo.json --output catalogo.json --report catalogo_report.md

Nota: i documenti con status diverso da "indicizzato" nell'indice di Fase 1
(es. "non_leggibile", "mancante") sono esclusi dalla catalogazione, restano
solo nell'indice di Fase 1. Se un documento esce dall'indice (es. diventa
"mancante"), la modalità incrementale lo rimuove anche dal catalogo.
"""

import argparse
import html as html_lib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Stopword e pulizia testo
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

# rumore ricorrente in questo tipo di corpus aziendale, poco informativo
# per distinguere un documento da un altro
STOPWORDS_NOISE = set("""
slide pag pagina pag. http https www com pptx docx xlsx pdf doc rtf csv
gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre
novembre dicembre lunedi martedi mercoledi giovedi venerdi sabato domenica
""".split())

STOPWORDS = STOPWORDS_IT | STOPWORDS_EN | STOPWORDS_NOISE

TOKEN_RE = re.compile(r"[a-zàèéìòù]{3,}", re.IGNORECASE)


def tokenize(text: str):
    if not text:
        return []
    text = text.lower()
    tokens = TOKEN_RE.findall(text)
    return [t for t in tokens if t not in STOPWORDS and not t.isdigit()]


# ---------------------------------------------------------------------------
# Estrazione testo per formato
# ---------------------------------------------------------------------------

def extract_pptx(path: Path) -> str:
    from pptx import Presentation
    prs = Presentation(str(path))
    parts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            parts.append(slide.notes_slide.notes_text_frame.text)
    return "\n".join(parts)


def extract_docx(path: Path) -> str:
    import docx
    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def extract_xlsx(path: Path, max_cells: int = 20000) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    parts = []
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip():
                    parts.append(cell.value)
                    n += 1
                    if n >= max_cells:
                        break
            if n >= max_cells:
                break
        if n >= max_cells:
            break
    return "\n".join(parts)


def extract_pdf(path: Path, max_pages: int = 60) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages[:max_pages]:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n".join(parts)


def extract_html(path: Path) -> str:
    from bs4 import BeautifulSoup
    raw = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator="\n")


def extract_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


EXTRACTORS = {
    "pptx": extract_pptx,
    "docx": extract_docx,
    "xlsx": extract_xlsx,
    "pdf": extract_pdf,
    "html": extract_html,
    "htm": extract_html,
    "csv": extract_plain,
    "md": extract_plain,
    "txt": extract_plain,
    "sql": extract_plain,
}


def extract_text(path: Path, extension: str):
    """Ritorna (testo, extraction_status)."""
    extractor = EXTRACTORS.get(extension)
    if extractor is None:
        return None, "formato_non_supportato"
    try:
        text = extractor(path)
        if text and text.strip():
            return text, "estratto"
        return None, "vuoto"
    except Exception as e:
        return None, f"errore: {type(e).__name__}"


def fallback_text(rel_path: str) -> str:
    """Segnale debole da nome file + percorso, per documenti senza testo estraibile."""
    return rel_path.replace("/", " ").replace("_", " ").replace("-", " ")


# ---------------------------------------------------------------------------
# TF-IDF (implementazione minimale, solo numpy)
# ---------------------------------------------------------------------------

def build_tfidf(token_lists, min_df=2, max_df=0.65):
    """TF-IDF con filtro sia sui termini iper-rari (min_df) sia su quelli
    iper-comuni (max_df, come frazione dei documenti). Nei corpus aziendali
    quasi ogni documento condivide un vocabolario di dominio (es. "data",
    "governance"): senza max_df quei termini dominano la similarità e
    schiacciano tutto in un unico cluster indistinto. min_df=1 quando il
    sottoinsieme è troppo piccolo perché df>=2 abbia senso."""
    n_docs = len(token_lists)
    doc_freq = Counter()
    for tokens in token_lists:
        doc_freq.update(set(tokens))

    if n_docs <= 2:
        min_df = 1

    max_df_count = max(min_df, math.ceil(max_df * n_docs)) if max_df is not None else n_docs
    vocab = [w for w, df in doc_freq.items() if min_df <= df <= max_df_count]
    if not vocab:
        # fallback: se il filtro max_df svuota il vocabolario (sottoinsiemi
        # piccoli e molto omogenei), rilassa e tieni solo il filtro min_df
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

    # L2 normalize per riga (per cosine similarity via dot product)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    return matrix, vocab


def top_terms_for_row(vector, vocab, top_n=8):
    idx = np.argsort(vector)[::-1][:top_n]
    return [vocab[i] for i in idx if vector[i] > 0]


# ---------------------------------------------------------------------------
# Clustering agglomerativo (average linkage), soglia scelta dal gap maggiore
# ---------------------------------------------------------------------------

def agglomerative_cluster(sim_matrix: np.ndarray, min_clusters=5, max_clusters=45):
    n = sim_matrix.shape[0]
    clusters = {i: [i] for i in range(n)}
    active = list(range(n))
    sim = sim_matrix.copy()
    np.fill_diagonal(sim, -np.inf)

    merge_log = []  # (similarity, n_clusters_dopo_il_merge)

    while len(active) > 1:
        # trova la coppia con similarità media più alta tra cluster attivi
        best_sim = -np.inf
        best_pair = None
        for a_idx in range(len(active)):
            for b_idx in range(a_idx + 1, len(active)):
                a, b = active[a_idx], active[b_idx]
                s = sim[a, b]
                if s > best_sim:
                    best_sim = s
                    best_pair = (a, b)

        if best_pair is None or best_sim == -np.inf:
            break

        a, b = best_pair
        merged_members = clusters[a] + clusters[b]
        clusters[a] = merged_members
        del clusters[b]
        active.remove(b)

        # ricalcola average-linkage tra il cluster unito 'a' e tutti gli altri attivi
        for c in active:
            if c == a:
                continue
            members_a = clusters[a]
            members_c = clusters[c]
            avg = float(np.mean([sim_matrix[i, j] for i in members_a for j in members_c]))
            sim[a, c] = avg
            sim[c, a] = avg
        sim[a, a] = -np.inf

        merge_log.append((best_sim, len(active)))

    return merge_log, clusters_history_to_final(merge_log, n, sim_matrix, min_clusters, max_clusters)


def clusters_history_to_final(merge_log, n_docs, sim_matrix, min_clusters, max_clusters):
    """Rifà il clustering fermandosi al numero di cluster scelto dal gap più
    grande nella sequenza di similarità di merge, entro [min_clusters, max_clusters]."""
    if not merge_log:
        return {0: list(range(n_docs))}

    # candidati: punti in cui n_clusters_dopo è dentro il range consentito
    candidates = [(sim, k) for sim, k in merge_log if min_clusters <= k <= max_clusters]
    if not candidates:
        # range non raggiunto (corpus troppo piccolo/omogeneo): usa il range più vicino disponibile
        candidates = merge_log

    # gap = quanto scende la similarità rispetto al merge successivo (più vicino a 1 cluster)
    # scegliamo il taglio subito PRIMA del salto più grande verso similarità più basse
    best_gap = -1
    best_k = candidates[0][1]
    for i in range(len(candidates) - 1):
        gap = candidates[i][0] - candidates[i + 1][0]
        if gap > best_gap:
            best_gap = gap
            best_k = candidates[i + 1][1]  # numero di cluster dopo il salto (più cluster = taglio più conservativo)

    return {"target_k": best_k}


def cluster_at_k(sim_matrix: np.ndarray, target_k: int):
    """Esegue l'agglomerative clustering fermandosi esattamente a target_k cluster."""
    n = sim_matrix.shape[0]
    clusters = {i: [i] for i in range(n)}
    active = list(range(n))
    sim = sim_matrix.copy()
    np.fill_diagonal(sim, -np.inf)

    while len(active) > target_k:
        best_sim = -np.inf
        best_pair = None
        for a_idx in range(len(active)):
            for b_idx in range(a_idx + 1, len(active)):
                a, b = active[a_idx], active[b_idx]
                s = sim[a, b]
                if s > best_sim:
                    best_sim = s
                    best_pair = (a, b)
        if best_pair is None:
            break
        a, b = best_pair
        clusters[a] = clusters[a] + clusters[b]
        del clusters[b]
        active.remove(b)
        for c in active:
            if c == a:
                continue
            avg = float(np.mean([sim_matrix[i, j] for i in clusters[a] for j in clusters[c]]))
            sim[a, c] = avg
            sim[c, a] = avg
        sim[a, a] = -np.inf

    return {cid: members for cid, members in clusters.items()}


# ---------------------------------------------------------------------------
# Suddivisione ricorsiva dei cluster troppo grandi
# ---------------------------------------------------------------------------
# In un corpus aziendale su un solo tema (es. "Data Governance"), il primo
# giro di clustering tende a produrre un cluster enorme e indistinto con
# tutto ciò che condivide il vocabolario di dominio, più pochi cluster
# piccoli per i documenti lessicalmente più "anomali". Un cluster da 190+
# documenti su 250 non è utile per restringere una ricerca: lo si riclusterizza
# ricorsivamente, ricalcolando il TF-IDF SOLO su quel sottoinsieme (così i
# termini di dominio, comuni a tutto il corpus, ridiventano discriminanti
# all'interno del sottoinsieme), finché ogni cluster foglia è sotto la soglia
# oppure non è più separabile in modo significativo.

SPLIT_THRESHOLD = 35
MAX_SPLIT_DEPTH = 3


def discover_clusters(token_lists, min_clusters, max_clusters, max_df=0.65, min_df=2):
    """Clusterizza il sottoinsieme di token_lists dato. Ritorna
    (lista di liste di indici LOCALI al sottoinsieme, vocab, matrix)."""
    matrix, vocab = build_tfidf(token_lists, min_df=min_df, max_df=max_df)
    sim_matrix = matrix @ matrix.T
    merge_log, decision = agglomerative_cluster(sim_matrix, min_clusters, max_clusters)
    target_k = decision["target_k"]
    final_clusters = cluster_at_k(sim_matrix, target_k)
    groups = [members for members in final_clusters.values()]
    return groups, vocab, matrix


def cluster_recursive(global_indices, token_lists, depth=0):
    """global_indices: indici nel token_lists completo da raggruppare.
    Ritorna la lista finale di cluster foglia (ognuno: lista di indici globali)."""
    n = len(global_indices)
    if n <= 2 or depth > MAX_SPLIT_DEPTH:
        return [global_indices]

    subset_tokens = [token_lists[i] for i in global_indices]
    min_clusters = 2
    max_clusters = max(2, min(15, n // 4))
    if max_clusters < min_clusters:
        return [global_indices]

    groups_local, _, _ = discover_clusters(subset_tokens, min_clusters, max_clusters)
    if len(groups_local) <= 1:
        # non separabile in modo significativo entro questo sottoinsieme
        return [global_indices]

    groups_global = [[global_indices[i] for i in grp] for grp in groups_local]
    leaves = []
    for grp in groups_global:
        if len(grp) > SPLIT_THRESHOLD:
            leaves.extend(cluster_recursive(grp, token_lists, depth + 1))
        else:
            leaves.append(grp)
    return leaves


def compute_generic_terms(token_lists, threshold=0.5):
    """Termini presenti in più di 'threshold' frazione di TUTTI i documenti
    del corpus (es. 'data', 'governance' in un corpus di Data Governance):
    hanno IDF minima e a volte dominano comunque un'etichetta per pura
    frequenza locale (TF alto), pur non discriminando nulla. Usati solo per
    filtrare le etichette leggibili, non per il clustering (che già usa
    max_df in build_tfidf)."""
    n_docs = len(token_lists)
    doc_freq = Counter()
    for tokens in token_lists:
        doc_freq.update(set(tokens))
    return {w for w, df in doc_freq.items() if df / n_docs > threshold}


def summarize_group(global_indices, token_lists, rel_paths, generic_terms=None, top_n=10,
                     label_prefix="", centroid_top_k=300):
    """Calcola etichetta, parole chiave, documento rappresentativo e centroide
    per un cluster foglia, con un TF-IDF ricalcolato SOLO su quel gruppo
    (max_df quasi disattivato: a questo livello vogliamo i termini più
    specifici possibile, non più il filtro sui termini di dominio). I
    termini generici di tutto il corpus (generic_terms) vengono esclusi solo
    dalla etichetta leggibile, non dal calcolo di similarità/rappresentante.

    Il centroide viene restituito anche come dizionario {termine: peso}
    (i centroid_top_k termini più pesanti) e salvato nel catalogo: è quello
    che permette, in un run successivo, di valutare se un documento nuovo o
    aggiornato appartiene a questo cluster senza dover rifare tutto il
    clustering da zero (vedi --catalog-in / run_incremental)."""
    subset_tokens = [token_lists[i] for i in global_indices]
    n = len(subset_tokens)
    min_df = 1 if n <= 2 else 2
    matrix, vocab = build_tfidf(subset_tokens, min_df=min_df, max_df=1.0)
    if not vocab or matrix.shape[1] == 0:
        label = f"{label_prefix}(nessun termine distintivo)" if label_prefix else "(nessun termine distintivo)"
        return label, [], global_indices[0], {}

    centroid = matrix.mean(axis=0)
    top_terms_raw = top_terms_for_row(centroid, vocab, top_n=max(top_n * 4, 30))
    if generic_terms:
        top_terms = [t for t in top_terms_raw if t not in generic_terms][:top_n]
        if not top_terms:
            top_terms = top_terms_raw[:top_n]
    else:
        top_terms = top_terms_raw[:top_n]

    sims_to_centroid = matrix @ centroid
    rep_local_idx = int(np.argmax(sims_to_centroid))
    rep_global_idx = global_indices[rep_local_idx]
    base_label = ", ".join(top_terms[:5]) if top_terms else "(nessun termine distintivo)"
    label = f"{label_prefix}{base_label}" if label_prefix else base_label

    centroid_dict = {}
    for i in np.argsort(centroid)[::-1]:
        if centroid[i] <= 0 or len(centroid_dict) >= centroid_top_k:
            break
        centroid_dict[vocab[i]] = float(centroid[i])

    return label, top_terms, rep_global_idx, centroid_dict


def cosine_sim_doc_to_centroid(tokens, centroid: dict):
    """Similarità approssimata tra un singolo documento (bag of words) e il
    centroide (dizionario termine->peso) di un cluster esistente. Usata in
    modalità incrementale per decidere se un documento nuovo/aggiornato
    appartiene a un cluster già noto, senza ricalcolare il TF-IDF di tutto
    il corpus. Approssimazione: il documento è pesato per pura frequenza
    (il centroide porta già in sé il peso IDF appreso quando il cluster è
    stato creato/aggiornato)."""
    if not tokens or not centroid:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    dot = 0.0
    doc_sq = 0.0
    for w, c in counts.items():
        tf = c / total
        doc_sq += tf * tf
        if w in centroid:
            dot += tf * centroid[w]
    if doc_sq == 0:
        return 0.0
    centroid_norm = math.sqrt(sum(v * v for v in centroid.values())) or 1.0
    doc_norm = math.sqrt(doc_sq) or 1.0
    return dot / (doc_norm * centroid_norm)


# ---------------------------------------------------------------------------
# Estrazione+tokenizzazione di un insieme di documenti (condivisa da
# modalità batch e incrementale)
# ---------------------------------------------------------------------------

def extract_and_tokenize(rel_paths, documents, root):
    token_lists = []
    extraction_status = {}
    for rel_path in rel_paths:
        entry = documents[rel_path]
        abs_path = root / rel_path
        ext = entry.get("extension", "")
        text, status = extract_text(abs_path, ext)
        if text is None:
            text = fallback_text(rel_path)
            status = f"solo_metadata ({status})"
        tokens = tokenize(text)
        token_lists.append(tokens)
        extraction_status[rel_path] = status
    return token_lists, extraction_status


def write_catalog_outputs(catalogo, extraction_status, output_path, report_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Catalogo scritto in: {output_path}")

    if report_path:
        cluster_info = catalogo["clusters"]
        # ordina per dimensione decrescente per leggibilità del report
        ordered = sorted(cluster_info.items(), key=lambda kv: -kv[1]["size"])
        lines = [f"# Catalogazione — {len(cluster_info)} cluster su {len(catalogo['documents'])} documenti", ""]
        for cid, info in ordered:
            lines.append(f"## Cluster {cid} — {info['label']}  ({info['size']} documenti)")
            lines.append("")
            lines.append(f"Parole chiave: {', '.join(info['top_terms'])}")
            lines.append("")
            lines.append(f"Documento rappresentativo: `{info['representative_document']}`")
            lines.append("")
            lines.append("Documenti:")
            for d in info["documents"]:
                status = extraction_status.get(d, "")
                flag = "" if status in ("", "estratto") else f"  _(({status}))_"
                lines.append(f"- {d}{flag}")
            lines.append("")
        Path(report_path).write_text("\n".join(lines), encoding="utf-8")
        print(f"Report scritto in: {report_path}")


# ---------------------------------------------------------------------------
# Modalità batch: clustering completo da zero
# ---------------------------------------------------------------------------

def run_batch(args):
    root = Path(args.root)
    index = json.load(open(args.index, encoding="utf-8"))
    documents = index["documents"]

    rel_paths = sorted([rp for rp, e in documents.items() if e.get("status") == "indicizzato"])
    print(f"Documenti indicizzati da catalogare: {len(rel_paths)}")

    token_lists, extraction_status = extract_and_tokenize(rel_paths, documents, root)

    n_estratti = sum(1 for s in extraction_status.values() if s == "estratto")
    n_fallback = len(extraction_status) - n_estratti
    print(f"  - testo estratto correttamente: {n_estratti}")
    print(f"  - solo metadata (fallback)     : {n_fallback}")

    top_groups, vocab, _ = discover_clusters(token_lists, args.min_clusters, args.max_clusters)
    print(f"Vocabolario (primo giro, senza termini troppo comuni/rari): {len(vocab)} termini")
    print(f"Cluster di primo livello: {len(top_groups)}")

    # qualsiasi cluster troppo grande per essere utile a restringere una
    # ricerca viene riclusterizzato ricorsivamente sul proprio sottoinsieme
    leaf_groups = []
    for grp in top_groups:
        if len(grp) > SPLIT_THRESHOLD:
            leaf_groups.extend(cluster_recursive(grp, token_lists, depth=1))
        else:
            leaf_groups.append(grp)

    n_split = sum(1 for grp in top_groups if len(grp) > SPLIT_THRESHOLD)
    if n_split:
        print(f"Cluster di primo livello sopra soglia ({SPLIT_THRESHOLD} doc) suddivisi ulteriormente: {n_split}")
    print(f"Numero di cluster finale: {len(leaf_groups)}")

    # termini presenti in oltre metà di TUTTO il corpus: poco utili come
    # etichetta anche quando localmente frequenti (es. "data", "governance")
    generic_terms = compute_generic_terms(token_lists, threshold=0.5)

    # etichetta, parole chiave, documento rappresentativo e centroide per
    # ogni cluster foglia
    cluster_info = {}
    doc_to_cluster = {}
    leaf_groups_sorted = sorted(leaf_groups, key=lambda g: -len(g))
    for new_id, members in enumerate(leaf_groups_sorted):
        label, top_terms, rep_global_idx, centroid_dict = summarize_group(
            members, token_lists, rel_paths, generic_terms=generic_terms, label_prefix=args.label_prefix
        )
        rep_doc = rel_paths[rep_global_idx]
        member_paths = [rel_paths[m] for m in members]
        cid = str(new_id)
        cluster_info[cid] = {
            "label": label,
            "top_terms": top_terms,
            "size": len(members),
            "representative_document": rep_doc,
            "documents": sorted(member_paths),
            "centroid": centroid_dict,
        }
        for p in member_paths:
            doc_to_cluster[p] = cid

    catalogo = {
        "meta": {
            "source_index": str(Path(args.index).resolve()),
            "root": str(root),
            "n_documents": len(rel_paths),
            "n_clusters": len(cluster_info),
            "vocab_size": len(vocab),
            "next_cluster_id": len(cluster_info),
        },
        "clusters": cluster_info,
        "documents": {
            rel_path: {
                "id": documents[rel_path]["id"],
                "content_hash": documents[rel_path].get("content_hash"),
                "cluster_id": doc_to_cluster[rel_path],
                "cluster_label": cluster_info[doc_to_cluster[rel_path]]["label"],
                "extraction_status": extraction_status[rel_path],
            }
            for rel_path in rel_paths
        },
    }

    write_catalog_outputs(catalogo, extraction_status, args.output, args.report)


# ---------------------------------------------------------------------------
# Modalità incrementale: parte da un catalogo già esistente (--catalog-in) e
# valuta SOLO i documenti nuovi o cambiati rispetto a quel catalogo:
# - se un documento è simile abbastanza (cosine >= --assign-threshold) al
#   centroide di un cluster esistente, viene assegnato lì (il cluster non
#   viene "rietichettato": l'etichetta resta quella eventualmente già
#   validata/rinominata a mano);
# - altrimenti finisce nel gruppo dei "non assegnabili", che a fine giro
#   viene clusterizzato per formare uno o più cluster NUOVI.
# I documenti che sono usciti dall'indice (status non più "indicizzato",
# es. diventati "mancante") vengono rimossi dal catalogo.
# ---------------------------------------------------------------------------

def run_incremental(args):
    root = Path(args.root)
    index = json.load(open(args.index, encoding="utf-8"))
    documents = index["documents"]
    old_catalog = json.load(open(args.catalog_in, encoding="utf-8"))
    old_docs = old_catalog["documents"]
    old_clusters = old_catalog["clusters"]

    rel_paths_all = sorted([rp for rp, e in documents.items() if e.get("status") == "indicizzato"])
    rel_paths_all_set = set(rel_paths_all)
    print(f"Documenti indicizzati (totale): {len(rel_paths_all)}")

    # documenti nuovi o con contenuto cambiato rispetto al catalogo precedente
    new_or_changed = []
    unchanged = []
    for rp in rel_paths_all:
        old_entry = old_docs.get(rp)
        new_hash = documents[rp].get("content_hash")
        if old_entry is None or old_entry.get("content_hash") != new_hash:
            new_or_changed.append(rp)
        else:
            unchanged.append(rp)

    # documenti che erano nel vecchio catalogo ma sono usciti dall'indice
    removed = [rp for rp in old_docs if rp not in rel_paths_all_set]

    print(f"  - invariati: {len(unchanged)}")
    print(f"  - nuovi o con contenuto cambiato da valutare: {len(new_or_changed)}")
    print(f"  - usciti dall'indice (rimossi dal catalogo): {len(removed)}")

    token_lists, extraction_status = extract_and_tokenize(new_or_changed, documents, root)
    token_by_path = dict(zip(new_or_changed, token_lists))

    # parti dai cluster esistenti (copiati) e ripulisci membri non più validi
    cluster_info = {cid: dict(info, documents=list(info["documents"])) for cid, info in old_clusters.items()}
    for cid, info in cluster_info.items():
        info["documents"] = sorted(set(info["documents"]) - set(removed) - set(new_or_changed))
        info["size"] = len(info["documents"])

    doc_to_cluster = {}
    doc_extraction_status = {}
    for rp in unchanged:
        old_entry = old_docs[rp]
        doc_to_cluster[rp] = old_entry["cluster_id"]
        doc_extraction_status[rp] = old_entry.get("extraction_status", "")

    assigned_count = 0
    unassigned = []
    for rp in new_or_changed:
        tokens = token_by_path[rp]
        best_cid, best_sim = None, -1.0
        for cid, info in cluster_info.items():
            sim = cosine_sim_doc_to_centroid(tokens, info.get("centroid", {}))
            if sim > best_sim:
                best_sim = sim
                best_cid = cid
        if best_cid is not None and best_sim >= args.assign_threshold:
            cluster_info[best_cid]["documents"].append(rp)
            cluster_info[best_cid]["size"] = len(cluster_info[best_cid]["documents"])
            doc_to_cluster[rp] = best_cid
            assigned_count += 1
        else:
            unassigned.append(rp)

    print(f"  - assegnati a cluster esistenti (soglia {args.assign_threshold}): {assigned_count}")
    print(f"  - non assegnabili a nessun cluster esistente: {len(unassigned)}")

    # i non assegnabili formano uno o più cluster nuovi
    next_id = old_catalog.get("meta", {}).get("next_cluster_id", len(old_clusters))
    generic_terms = compute_generic_terms(token_lists, threshold=0.5) if token_lists else set()

    if unassigned:
        unassigned_tokens = [token_by_path[rp] for rp in unassigned]
        n = len(unassigned)
        if n >= 4:
            min_c = 1
            max_c = max(1, n // 3)
            groups_local, _, _ = discover_clusters(unassigned_tokens, min_c, max_c)
            new_groups = [[unassigned[i] for i in grp] for grp in groups_local]
        else:
            # troppo pochi documenti per un clustering interno sensato:
            # ognuno diventa il proprio cluster (stessa convenzione già in
            # uso per i cluster singoli prodotti dal run in modalità batch)
            new_groups = [[rp] for rp in unassigned]

        for grp in new_groups:
            grp_indices = list(range(len(grp)))
            grp_tokens = [token_by_path[rp] for rp in grp]
            label, top_terms, rep_local_idx, centroid_dict = summarize_group(
                grp_indices, grp_tokens, grp, generic_terms=generic_terms, label_prefix=args.label_prefix
            )
            cid = str(next_id)
            next_id += 1
            cluster_info[cid] = {
                "label": label,
                "top_terms": top_terms,
                "size": len(grp),
                "representative_document": grp[rep_local_idx],
                "documents": sorted(grp),
                "centroid": centroid_dict,
            }
            for rp in grp:
                doc_to_cluster[rp] = cid
        print(f"  - nuovi cluster creati per i non assegnabili: {len(new_groups)}")

    for rp in new_or_changed:
        doc_extraction_status[rp] = extraction_status[rp]

    # rimuovi cluster rimasti vuoti (tutti i loro membri erano "removed")
    cluster_info = {cid: info for cid, info in cluster_info.items() if info["size"] > 0}

    catalogo = {
        "meta": {
            "source_index": str(Path(args.index).resolve()),
            "root": str(root),
            "n_documents": len(rel_paths_all),
            "n_clusters": len(cluster_info),
            "vocab_size": old_catalog.get("meta", {}).get("vocab_size"),
            "next_cluster_id": next_id,
        },
        "clusters": cluster_info,
        "documents": {
            rp: {
                "id": documents[rp]["id"],
                "content_hash": documents[rp].get("content_hash"),
                "cluster_id": doc_to_cluster[rp],
                "cluster_label": cluster_info[doc_to_cluster[rp]]["label"],
                "extraction_status": doc_extraction_status.get(rp, ""),
            }
            for rp in rel_paths_all
        },
    }

    write_catalog_outputs(catalogo, doc_extraction_status, args.output, args.report)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Fase 2 - Catalogazione (clustering documenti)")
    ap.add_argument("--index", required=True, help="Indice prodotto dalla Fase 1 (JSON)")
    ap.add_argument("--root", required=True, help="Cartella radice dei documenti (deve corrispondere a quella indicizzata)")
    ap.add_argument("--output", required=True, help="Percorso del catalogo di output (JSON)")
    ap.add_argument("--report", help="Percorso opzionale per un report markdown dei cluster")
    ap.add_argument("--min-clusters", type=int, default=5)
    ap.add_argument("--max-clusters", type=int, default=45)
    ap.add_argument("--label-prefix", default="", help='Prefisso da anteporre a tutte le etichette generate, es. "Data Governance - "')
    ap.add_argument("--catalog-in", help="Catalogo esistente (JSON) da aggiornare in modo incrementale invece di riclusterizzare tutto da zero")
    ap.add_argument("--assign-threshold", type=float, default=0.15,
                     help="Similarità coseno minima per assegnare un documento nuovo/aggiornato a un cluster esistente (modalità incrementale)")
    args = ap.parse_args()

    if args.catalog_in:
        run_incremental(args)
    else:
        run_batch(args)


if __name__ == "__main__":
    main()
