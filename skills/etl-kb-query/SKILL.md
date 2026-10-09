---
name: etl-kb-query
description: Interroga una knowledge base costruita con la pipeline ETL documentale a 5 fasi (Indicizzazione, Catalogazione, Estrazione, Knowledge Layer, Cronistoria), riconoscibile dalla cartella "Output/ETL_Documentale" dentro un progetto e da file come catalogo_*.json, estrazione_*.json, knowledge_layer_*.json, cronistoria_*.json. Usa SEMPRE questa skill quando l'utente fa una domanda di contenuto su un progetto che ha questa pipeline — es. "cosa è stato deciso su X", "chi si occupa di Y", "qual è lo stato attuale di Z", "quando è cambiata la decisione su...", "che sistemi/normative sono coinvolti in...", anche se l'utente non nomina esplicitamente "knowledge base" o i file JSON. NON usarla per rigenerare o estendere la pipeline stessa (quello richiede gli script della cartella ETL_Documentale del progetto, non questa skill) — questa skill è solo per LEGGERE e rispondere, seguendo il percorso inverso rispetto a come la base è stata costruita.
---

# Interrogare una knowledge base ETL documentale

Questa skill risponde a domande di contenuto attingendo a una knowledge
base già costruita da una pipeline a 5 fasi (Indicizzazione → Catalogazione
→ Estrazione → Knowledge Layer → Cronistoria). L'idea è percorrere quelle
fasi **al contrario**: si parte dal livello più sintetico e temporale
(Cronistoria) e si scende verso il documento originale solo se necessario,
invece di leggere tutto il corpus da zero ogni volta.

Perché al contrario: la Cronistoria e il Knowledge Layer esistono apposta
per evitare di rileggere centinaia di documenti a ogni domanda — dicono
subito "quando" e "in quale documento" si trova l'informazione più
pertinente e più recente. Saltare questi livelli e andare a caso nei
documenti originali vanifica il lavoro fatto e rischia di citare una
versione superata di una decisione.

## Prima di rispondere: leggi lo schema dei file

Se non l'hai già fatto in questa sessione, leggi `references/schemas.md`
per conoscere la struttura esatta di ciascun file (campi, significato di
`tipo`, `sotto_tipo`, `fonte_data`, ecc.). Rispondere senza aver chiaro
cosa contiene ogni livello porta a citare campi sbagliati o a inventare
struttura che non esiste.

## Passo 0 — Localizza la knowledge base e controlla la copertura reale

Queste pipeline vengono quasi sempre costruite in modo incrementale (un
"pilota" su pochi cluster, poi eventualmente esteso). Prima di cercare
qualunque informazione, esegui:

```bash
python3 scripts/locate_kb.py --root "<cartella Progetti>" [--project <NomeProgetto>]
```

oppure, se conosci già la cartella esatta:

```bash
python3 scripts/locate_kb.py --etl-dir "<path/Output/ETL_Documentale>"
```

L'output ti dice, per ciascun cluster del catalogo: quanti documenti
contiene e quanti sono stati effettivamente processati da Estrazione
(`coperto: "completo" | "parziale" | "non_coperto"`). Tieni a mente questo
quadro per tutto il resto della ricerca: se la domanda cade in un cluster
`non_coperto`, la Cronistoria e il Knowledge Layer semplicemente non hanno
nulla su quel tema — non è un'assenza di informazione, è un'assenza di
elaborazione. In questo caso vai direttamente al Passo 4b.

## Passo 0bis — Leggi le correzioni dell'utente

Se `locate_kb.py` riporta un file `correzioni` con `n_correzioni_attive`
maggiore di zero, leggilo (è piccolo) prima di cercare: contiene
correzioni, documenti segnalati come non affidabili e decisioni di
perimetro date dall'utente (vedi `references/schemas.md`). Sono
annotazioni, non sostituiscono i dati dei file di fase: quando una fonte
che stai per citare compare in `riferimento` di una correzione `attiva`,
la correzione ha la precedenza sul dato originale e va citata nella
risposta (id, data, autore). Ignora le voci `superata`. Se una correzione
contraddice un documento più recente, non risolvere in silenzio: mostra
entrambi e segnalalo.

## Passo 1 — Interpreta la domanda

Prima di cercare, capisci cosa serve davvero. In particolare individua:

- **Argomento/entità**: una persona, un sistema/tool, una normativa, un
  processo, un tema generale?
- **Ambito temporale**: la domanda vuole la situazione **attuale/più
  recente** ("qual è lo stato di..."), oppure un punto preciso nel tempo
  ("cosa diceva il documento di ottobre..."), oppure **l'evoluzione**
  ("come si è arrivati a...", "è cambiato qualcosa su...")?
- **Progetto**: se lavori con più progetti/knowledge base nella stessa
  sessione ed è ambiguo a quale progetto si riferisca la domanda, chiedi.

Se la domanda è chiaramente scoped (nomina un documento, una data, una
persona precisa), non serve fare altre domande: procedi. Chiedi solo
quando l'ambiguità cambierebbe davvero dove cerchi (es. "attuale" vs
"storico" ti fa scegliere se fermarti al primo risultato o seguire tutta
la catena di `possibili_aggiornamenti_decisioni`).

### Espandi la domanda in varianti di ricerca

Prima di cercare nei file, genera mentalmente 3-5 formulazioni alternative
distinte dell'argomento/entità individuato: sinonimi, sigla vs nome per
intero, termine tecnico vs gergale, variante morfologica (es. "firma
digitale" → "firma elettronica", "FEQ", "sottoscrizione documenti").
Usa tutte queste varianti — non solo le parole esatte della domanda
originale — quando cerchi per parola chiave in Catalogo, Knowledge Layer
(`nome_canonico`/`alias`) ed Estrazione nei passi successivi (2, 3, 3bis,
4a). Questo evita di concludere "non trovato" solo perché l'utente ha
usato un termine diverso da quello scritto nei documenti originali — è la
causa più comune di falsi negativi in una ricerca puramente lessicale.
Non serve scrivere le varianti da nessuna parte né mostrarle all'utente:
è un passo interno che allarga il raggio delle ricerche successive.

### Domande larghe o multi-tema: scomponi prima di cercare

Se la domanda è in realtà una checklist con molti sotto-punti distinti
(es. una mail di un cliente con 6-10 richieste tipo "come siete partiti,
che modello di governance avete, come misurate il valore, che criteri
avete usato per scegliere la piattaforma..."), NON trattarla come una
singola ricerca: scomponila nei suoi sotto-temi e tratta ciascuno come una
query a parte per i Passi 2/3/3bis/4a. Un solo giro di ricerca con le
parole della domanda complessiva tende a fermarsi ai primi risultati più
"generici" (es. i documenti di piano/timeline) e a non arrivare mai ai
documenti più verticali e tecnici (appendici di processo, manuali tool,
policy specifiche), che spesso non sono nemmeno rappresentati come entità
in Knowledge Layer/Cronistoria — esistono solo dentro l'Estrazione, quindi
si trovano solo cercandoli per il loro sotto-tema specifico.

Per questo genere di domande, usa il fallback TF-IDF del Passo 3bis
**in modo proattivo per ogni sotto-tema**, non solo come ultima risorsa
quando Cronistoria/Knowledge Layer non trovano nulla: anche quando un
sotto-tema più generale (es. "governance") ha già dei candidati, un
sotto-tema più specifico (es. "criteri di selezione della piattaforma",
"master data management", "metriche di adozione") può non avere nessuna
entità dedicata in Knowledge Layer e va comunque cercato a parte con
`semantic_candidates.py`, una query per sotto-tema. Il costo di qualche
chiamata in più è basso rispetto al rischio di consegnare una risposta
con buchi su metà dei sotto-temi solo perché non modellati come entità.

## Passo 2 — Cronistoria: individua il quando

Apri `cronistoria_*.json` (path da `locate_kb.py`) e guarda in quest'ordine:

1. `possibili_aggiornamenti_decisioni` — se il tema compare qui (cerca per
   parole chiave nel campo `tema` e nei `testo`), hai già la catena
   decisione precedente → successiva → eseguita, con livello di
   confidenza. Questo è quasi sempre il modo più rapido di rispondere a
   domande sull'evoluzione di una decisione o sul suo stato attuale.
2. `avvisi_qualita_dati` — controlla se qualcuno dei documenti che stai per
   usare come fonte è segnalato qui (date contraddittorie, duplicati,
   correzioni di perimetro, contenuti fuori scope). Se sì, tienine conto
   nella risposta invece di ignorarlo.
3. `timeline_decisioni_cluster1` (o nome equivalente) — l'elenco mecanico
   ordinato per data; utile se la domanda è più ampia ("cosa è successo
   tra marzo e maggio su...") o se i due punti sopra non bastano.

Se il tema non compare in nessuno dei tre, la Cronistoria semplicemente non
lo tratta — non vuol dire che l'informazione non esista nei documenti,
vuol dire che non è (ancora) una decisione tracciata. Vai al passo 3.

## Passo 3 — Knowledge Layer: individua le entità e i documenti candidati

Apri `knowledge_layer_*.json` e cerca l'entità (persona / sistema_tool /
riferimento_normativo) per `nome_canonico` o `alias` — usa una ricerca
case-insensitive e tollerante a piccole varianti di nome, dato che il
Knowledge Layer normalizza alias diversi sotto un unico nome canonico
(vedi `references/schemas.md` per come funziona la canonicalizzazione).

Per l'entità trovata, guarda `menzioni` (tutti i documenti che la citano,
con data e contesto) e `ultima_menzione`. Questo ti dà direttamente
l'elenco dei documenti candidati da cui costruire la risposta, già
ordinabile per data — molto più efficiente che scorrere l'intero catalogo.

Se la domanda riguarda "chi fa cosa" o "che sistemi sono coinvolti in un
processo", questo livello spesso basta da solo, incrociando più entità
(es. tutte le persone/sistemi che compaiono negli stessi documenti).

## Passo 3bis — Fallback lessicale (TF-IDF) quando il match esatto non basta

Se dopo Passo 2 e Passo 3 (con tutte le varianti del Passo 1) non hai
candidati, oppure ne hai pochi e poco convincenti, non concludere subito
che l'informazione non esiste: il tema potrebbe essere descritto nei
documenti con parole diverse da quelle di `label`/`nome_canonico`/`alias`
(che coprono bene entità nominate esplicitamente, ma non temi descritti
solo a parole nel testo libero). Questo è anche il motivo per cui, su
domande larghe/multi-tema (vedi Passo 1), questo passo va eseguito per
ogni sotto-tema a prescindere da quanti candidati hai già trovato per gli
altri sotto-temi — non solo quando la ricerca è totalmente a vuoto. Usa:

```bash
python3 scripts/semantic_candidates.py --etl-dir "<path/Output/ETL_Documentale>" \
    --query "<domanda o parole chiave, incluse le varianti del Passo 1>" [--top 10]
```

Lo script costruisce una rappresentazione TF-IDF sui campi testuali liberi
di `estrazione_*.json` (`argomento`, `contenuti_trattati`, `decisioni`,
`parole_chiave` quando presente) e ritorna i documenti più simili alla
query, con punteggio di similarità coseno. È un fallback lessicale (non un
vero motore semantico): usalo per allargare la rete di candidati da
verificare al Passo 4a, non come fonte diretta di una risposta — la
similarità testuale suggerisce dove guardare, non conferma un fatto.

**Limite noto — non fidarti ciecamente di punteggi bassi.** Il punteggio
TF-IDF dipende dalla ricchezza dei campi liberi in Estrazione per quel
documento. Alcuni documenti (spesso pptx con poco testo estratto) hanno
`argomento` generico e `parole_chiave`/`sistemi_tool_citati` vuoti: per
questi il punteggio resterà basso per qualsiasi query, non perché il tema
non sia rilevante ma perché l'Estrazione non ha catturato un vocabolario
sufficiente. Se per un sotto-tema importante (Passo 1) i punteggi restano
tutti bassi (es. sotto 0.15) o il documento in cima ai risultati sembra
scollegato dal tema, non fermarti al fallback TF-IDF: apri direttamente
`estrazione_*.json` e scorri i campi `argomento`/titolo dei documenti del
cluster pertinente (identificato via `catalogo_*.json` → `cluster_label`)
per un controllo manuale mirato — un titolo di documento spesso rivela la
pertinenza meglio del punteggio TF-IDF quando il contenuto libero è povero.
Se anche questo fallback non produce nulla di pertinente, il tema
probabilmente non è nel perimetro coperto: vai al Passo 4b.

## Passo 4a — Estrazione + Catalogo: conferma nel documento esatto

Con i documenti candidati in mano (dal Passo 2 e/o 3), apri
`estrazione_*.json` e leggi la voce esatta per quel percorso documento
(dentro `avanzamento` o `contenuto` secondo lo schema — vedi
`references/schemas.md`). Qui trovi il fatto preciso, non solo la
menzione.

Se ci sono più documenti candidati con informazioni che si contraddicono,
il criterio di base resta "vince il documento più recente" (per data nel
testo, non per data di modifica file, quando disponibile — controlla
`fonte_data`/`data_fonte` di ciascuna voce). Se il progetto ha una
`CLAUDE.md` con questa regola già scritta esplicitamente, seguila; se non
c'è, applicala comunque come buon senso di default e dillo nella risposta.

Questa regola binaria funziona bene quando i candidati sono 1-2 e le date
sono certe e comparabili. Con **3 o più candidati in conflitto**, o quando
una o più date sono parziali/testuali (es. "Maggio 2026", "II trimestre")
invece di `YYYY-MM-DD` esatte, non applicarla ciecamente al primo confronto
a coppie: prima ordina tutti i candidati per data (trattando le date
parziali come un intervallo, non un punto preciso, e segnalando quando due
candidati si sovrappongono nel tempo e quindi non sono chiaramente
ordinabili), poi controlla anche la pertinenza tematica di ciascuno
rispetto alla domanda specifica (un documento più vecchio ma focalizzato
esattamente sul tema può essere più utile citato insieme al più recente,
non necessariamente scartato) — l'idea, ispirata a come altri sistemi di
retrieval combinano recency e pertinenza invece di un cutoff netto, è
presentare la catena "chi ha detto cosa e quando" quando la sola data non
basta a dare un vincitore netto, invece di forzare una risposta a un solo
documento. In questi casi più ambigui, dillo nella risposta: mostra almeno
i 2-3 candidati più recenti/pertinenti con le rispettive date (anche
parziali) invece del solo "vincitore", così chi legge può giudicare da sé
se il conflitto è reale o solo apparente.

Usa `catalogo_*.json` solo se ti serve capire il contesto più ampio (quali
altri documenti simili esistono nello stesso cluster) o se serve
confermare che un documento appartiene davvero al cluster/tema che stai
cercando.

## Passo 4b — Fuori perimetro: quando la copertura non basta

Se il Passo 0 ha già segnalato che il cluster/tema è `non_coperto` (o
`parziale` e i documenti mancanti sono proprio quelli rilevanti), non
inventare una risposta basata solo sulle etichette del catalogo. Invece:

1. Usa `catalogo_*.json` per trovare, per parole chiave nella `label` e nei
   `documents` (nomi file), i documenti candidati nei cluster non coperti.
2. Dillo esplicitamente all'utente: l'informazione potrebbe essere in
   quei documenti, ma non sono ancora passati da Estrazione/Knowledge
   Layer/Cronistoria, quindi la risposta richiede di aprirli direttamente
   (offri di farlo, se ha senso) oppure di estendere prima la pipeline.
3. Non presentare come "non esiste nel progetto" qualcosa che in realtà è
   solo "non ancora processato" — è una distinzione importante per chi
   userà la risposta per prendere decisioni.

## Passo 5 — Prepara la risposta

Nella risposta finale:

- Cita sempre **documento + data** esatti da cui viene l'informazione
  (non solo "secondo la knowledge base"). Usa il percorso relativo del
  documento come appare nel catalogo/estrazione, così l'utente può
  ritrovarlo facilmente.
- Se la domanda riguardava l'evoluzione di una decisione, riassumi la
  catena (precedente → successiva → eseguita) in poche righe, non solo il
  punto finale — è spesso quello che rende la risposta davvero utile.
- Se una correzione attiva (Passo 0bis) riguarda una fonte che hai usato,
  citala: "Correzione C003 del 2026-08-03: …".
- Se hai usato un documento segnalato in `avvisi_qualita_dati`, menziona
  brevemente il caveat (es. "nota: questo documento ha due date di
  aggiornamento diverse nel testo").
- Se la risposta è parziale per limiti di copertura (Passo 4b), dillo in
  una riga, senza trasformarla nel fulcro della risposta.
- Non serve creare file per rispondere — questa skill produce risposte in
  chat con citazione della fonte, salvo che l'utente chieda esplicitamente
  un documento/report.

## Riferimenti

- `references/schemas.md` — struttura esatta dei 5 file (leggi prima di
  interrogare la base se non conosci già questi schemi)
- `scripts/locate_kb.py` — trova le cartelle ETL_Documentale e calcola la
  copertura reale (Passo 0)
- `scripts/etl_pipeline/correzioni.py` (repo `kb_management`) — gestione del
  registro correzioni; in questa skill serve solo leggerlo (Passo 0bis)
- `scripts/semantic_candidates.py` — fallback lessicale TF-IDF su
  Estrazione quando il match esatto per nome/alias non basta (Passo 3bis)
