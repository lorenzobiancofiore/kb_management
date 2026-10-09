# Schemi dei file della pipeline ETL documentale

Ogni knowledge base costruita con questa pipeline vive in una cartella
`Progetti/<NomeProgetto>/Output/ETL_Documentale/` e contiene fino a 5 file
principali (uno per fase). Usa `scripts/locate_kb.py` per trovarli e capire
la copertura effettiva prima di leggerli — i nomi esatti dei file variano
da progetto a progetto (es. `catalogo_ProgettoDG.json`,
`estrazione_pilota_cluster1_2.json`), lo script li individua per pattern.

## Fase 1 — Indice (`index_*.json`)

Elenco di tutti i documenti scansionati con `content_hash`, stato
(`indicizzato` / `non_leggibile`) e una `history` di eventi (nuovo,
aggiornato, invariato, mancante). Raramente serve leggerlo per rispondere a
una domanda di contenuto — è la base per Catalogazione. Utile solo se un
documento sembra "sparito" o se serve la cronologia tecnica dei file.

## Fase 2 — Catalogo (`catalogo_*.json`)

```json
{
  "clusters": {
    "<id_cluster>": {
      "label": "Prefisso - parola1, parola2, ...",
      "tipo": "avanzamento" | "contenuto" | null,
      "documents": ["percorso/relativo/Doc1.pptx", "..."],
      "representative_document": "...",
      "size": 23
    }
  },
  "documents": { "<percorso_relativo>": {"cluster": "<id_cluster>", ...} },
  "meta": {"n_clusters": 48, "n_documents": 276, "root": "..."}
}
```

- `tipo: "avanzamento"` → documenti tipo SAL/meeting con decisioni,
  partecipanti, action item — vanno nello schema avanzamento di Estrazione
  e nella timeline della Cronistoria.
- `tipo: "contenuto"` → presentazioni/documenti tematici, procedure,
  normative — schema contenuto di Estrazione, MAI nella timeline mecanica
  della Cronistoria (anche se contengono decisioni: quelle vanno segnalate
  solo come `avvisi_qualita_dati`, non nella timeline, per scelta di
  design già presa su questo progetto — verifica se vale anche altrove).
- L'`id_cluster` (chiave del dict `clusters`) è la verità di base per il
  perimetro — non fidarti di nomi di file come `estrazione_pilota_cluster1_2`
  che possono coincidere per caso con gli id cluster reali ma vanno sempre
  verificati.

## Fase 3 — Estrazione (`estrazione_*.json`)

```json
{
  "meta": {...},
  "avanzamento": {
    "<percorso_relativo_documento>": {
      "data_documento": "YYYY-MM-DD",
      "partecipanti": ["Nome Cognome", ...],
      "contenuti_trattati": ["..."],
      "decisioni": ["..."],
      "rischi_blocchi": ["..."],
      "prossimi_passi": ["..."],
      "action_item": ["..."],
      "data_fonte": "testo" | "data_modifica_file (approssimata)" | "..."
    }
  },
  "contenuto": {
    "<percorso_relativo_documento>": {
      "sotto_tipo": "glossario"|"normativa"|"formazione"|"procedura"|"altro"|"analisi_funzionale",
      "argomento": "riassunto libero",
      "processi_attivita": ["..."],
      "ruoli_responsabilita": ["..."],
      "sistemi_tool_citati": ["..."],
      "riferimenti_normativi": ["..."],
      "versione_data_validita": "YYYY-MM-DD o testo descrittivo",
      "versione_data_fonte": "testo" | "data_modifica_file (approssimata)" | "...",
      "parole_chiave": ["..."]
    }
  }
}
```

Questo è il livello dei FATTI grezzi per singolo documento — la fonte più
dettagliata e più vicina al testo originale, senza incroci fra documenti.
Se la domanda riguarda "cosa dice esattamente il documento X", la risposta
è quasi sempre qui (o nel documento originale, se l'estrazione non basta).

- `parole_chiave` (in entrambi gli schemi) è **opzionale** — presente solo
  nei documenti estratti dopo l'introduzione di questo campo, quindi la
  sua assenza non è un errore su documenti più vecchi. Quando presente,
  contiene sinonimi/varianti/sigle pensate per la ricerca (non un riassunto
  del tema) e viene incluso nel corpus testuale usato dal fallback TF-IDF
  di `scripts/semantic_candidates.py` (Passo 3bis della skill).

## Fase 4 — Knowledge Layer (`knowledge_layer_*.json`)

```json
{
  "persone": [
    {
      "id": "nome-cognome",
      "tipo": "persona",
      "nome_canonico": "Nome Cognome",
      "alias": [],
      "menzioni": [
        {"documento": "...", "tipo_documento": "avanzamento|contenuto",
         "data": "...", "fonte_data": "...", "contesto": "..."}
      ],
      "ultima_menzione": {...} | null
    }
  ],
  "sistemi_tool": [ {"id": "...", "tipo": "sistema_tool", "nome_canonico": "...", "alias": [...], "menzioni": [...], "ultima_menzione": {...}} ],
  "riferimenti_normativi": [ {"id": "...", "tipo": "riferimento_normativo", "nome_canonico": "...", "famiglia": "...", "menzioni": [...], "ultima_menzione": {...}} ]
}
```

Questo è il livello delle ENTITÀ trasversali — chi/cosa/quale norma è
citato, in quali documenti, con che frequenza. `ultima_menzione` è già
calcolato ma solo per date in formato esatto `YYYY-MM-DD`: le date
parziali/testuali ("Maggio 2026") sono escluse dal calcolo automatico, per
cui vanno controllate a mano quando è quella la menzione più recente.

Usa questo livello per rispondere a domande del tipo "chi si occupa di X",
"che sistemi sono coinvolti in Y", "quali documenti citano la normativa Z"
— e per ottenere subito l'elenco dei documenti candidati da controllare.

## Fase 5 — Cronistoria (`cronistoria_*.json`)

```json
{
  "timeline_decisioni_cluster1": [
    {"documento": "...", "data": "YYYY-MM-DD", "fonte_data": "...", "decisioni": ["..."]}
  ],
  "possibili_aggiornamenti_decisioni": [
    {
      "tema": "...",
      "decisione_precedente": {"data": "...", "documento": "...", "testo": "..."},
      "decisione_successiva": {"data": "...", "documento": "...", "testo": "..."},
      "eseguita_in": {"data": "...", "documento": "...", "testo": "..."},
      "confidenza": "bassa|media|media-alta|alta",
      "nota": "..."
    }
  ],
  "avvisi_qualita_dati": [
    {"descrizione": "...", "documenti": ["..."]}
  ]
}
```

- `timeline_decisioni_cluster1` è mecanica (ordinata per data/mtime),
  scoped solo ai documenti "avanzamento" — è l'elenco grezzo, non ancora
  interpretato, delle decisioni nel tempo.
- `possibili_aggiornamenti_decisioni` è il livello INTERPRETATO: collega
  decisioni che si evolvono nel tempo su uno stesso tema, con un livello di
  confidenza. Parti sempre da qui se la domanda è "come si è arrivati alla
  situazione attuale su X" o "questa decisione è ancora valida?".
- `avvisi_qualita_dati` segnala problemi noti (date contraddittorie,
  documenti duplicati, contenuti fuori scope, correzioni di perimetro) —
  controlla sempre se uno dei documenti che stai per citare compare qui
  prima di usarlo come fonte definitiva.

Nota bene: il nome del file (spesso con `pilota` dentro) e il campo
`timeline_decisioni_cluster1` ricordano che, storicamente, questa fase è
stata costruita partendo da un sottoinsieme del corpus (un pilota), non
dall'intero catalogo — da qui l'importanza di controllare la copertura
reale con `locate_kb.py` prima di trattare l'assenza di un'informazione
come "non esiste" invece che "non è stata ancora processata".


## Registro correzioni (`correzioni_*.json`) — opzionale

Non è una fase della pipeline: è il registro delle correzioni e dei giudizi
dati dall'utente sulla knowledge base ("questo documento non va usato",
"la data corretta è…", "il cluster X va trattato come contenuto"). Può non
esistere (progetti senza correzioni) e `locate_kb.py` riporta path e numero
di voci attive.

```json
{
  "meta": {"versione": 1},
  "correzioni": [
    {
      "id": "C001",
      "tipo": "correzione" | "documento_non_affidabile" | "perimetro" | "nota",
      "riferimento": {"documento": "percorso/relativo", "entita": "nome_canonico", "tema": "..."},
      "testo": "cosa è stato corretto/deciso",
      "motivo": "perché",
      "autore": "...",
      "data": "YYYY-MM-DD",
      "stato": "attiva" | "superata",
      "superata_il": "YYYY-MM-DD",
      "sostituita_da": "C007"
    }
  ]
}
```

- Sono **annotazioni**: non modificano mai catalogo, estrazione, knowledge
  layer o cronistoria. Chi interroga le legge e le cita accanto alla fonte
  a cui si riferiscono (`riferimento` contiene almeno uno tra `documento`,
  `entita`, `tema`).
- Una correzione non si cancella ma si marca `superata`; solo "Dimentica:"
  esplicito dell'utente la elimina davvero.
- Gestione tramite `scripts/etl_pipeline/correzioni.py` (add, list, find,
  supersede, forget).
