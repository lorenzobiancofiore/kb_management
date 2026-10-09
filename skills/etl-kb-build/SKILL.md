---
name: "etl-kb-build"
description: "Crea o estende la pipeline ETL documentale a 5 fasi (Indicizzazione, Catalogazione, Estrazione, Knowledge Layer, Cronistoria) più i passi derivati Relazioni e Rileva aggiornamenti su temi tracciati, più il passo di presentazione Ontology Viewer HTML. È il verso opposto di etl-kb-query (che legge, questa costruisce/aggiorna). Usa sempre questa skill quando l'utente vuole avviare da zero la pipeline su un progetto senza cartella Output/ETL_Documentale, oppure aggiungere nuovi documenti/cluster a una pipeline già esistente (es. \"ho caricato altri documenti, aggiorna la knowledge base\", \"estendi la pipeline con questi nuovi file\", \"fai partire l'ETL su questo nuovo progetto\"), anche se l'utente non nomina esplicitamente \"pipeline\" o le 5 fasi. NON usarla per rispondere a domande di contenuto sulla knowledge base già costruita — quello è compito di etl-kb-query."
---

# Costruire o estendere una knowledge base ETL documentale

Questa skill è il verso opposto di `etl-kb-query`: mentre quella LEGGE una
knowledge base già costruita, questa la CREA o la ESTENDE. Usala quando
l'utente vuole:

- avviare da zero la pipeline ETL documentale a 5 fasi (Indicizzazione →
  Catalogazione → Estrazione → Knowledge Layer → Cronistoria) su un progetto
  che non ha ancora una cartella `Output/ETL_Documentale`;
- aggiungere nuovi documenti o nuovi cluster a una pipeline già esistente
  (es. "ho caricato altri documenti, aggiorna la knowledge base");
- far girare di nuovo il passo derivato "Relazioni tra entità" dopo aver
  aggiornato Knowledge Layer/Estrazione.

Non usarla per rispondere a domande di contenuto ("cosa è stato deciso su
X") — quello è il compito di `etl-kb-query`. Se la pipeline non esiste
ancora, questa skill la crea; se esiste già, la estende; in entrambi i casi
il passo finale è sempre lo stesso identico "attrezzo" (Fase 3-5), quindi
tratta il bootstrap come "estensione a partire da zero documenti coperti"
più uno step iniziale in più.

## Perché seguire questo ordine e non un altro

Le 5 fasi hanno una dipendenza stretta: Catalogazione ha bisogno
dell'Indice, Estrazione lavora cluster per cluster del Catalogo, Knowledge
Layer e Cronistoria derivano dall'Estrazione. Saltare fasi o improvvisare
uno schema diverso da quello già in uso nel progetto rompe la compatibilità
con `etl-kb-query` e con qualunque report già scritto. Se il progetto ha
già una pipeline, la priorità assoluta è restare coerenti con le
convenzioni che già usa (nomi di file, schema dei campi, regole di
canonicalizzazione) — non reinventarle.

## Passo 0 — Bootstrap o estensione?

Controlla se esiste già `Progetti/<NomeProgetto>/Output/ETL_Documentale/`
con almeno un `index_*.json` e un `catalogo_*.json`.

- **Non esiste** → vai a "Modalità A — Bootstrap da zero".
- **Esiste** → vai a "Modalità B — Estensione incrementale". Prima di
  iniziare, calcola la copertura reale con la logica di
  `scripts/locate_kb.py` di `etl-kb-query` (se quella skill è installata,
  usa direttamente il suo script; altrimenti replica questa logica: per
  ogni cluster del catalogo, calcola quanti documenti sono già coperti da
  Estrazione — `"completo"`, `"parziale"` o `"non_coperto"` — così sai
  esattamente cosa manca prima di rifare lavoro già fatto).

## Modalità A — Bootstrap da zero

1. **Struttura cartelle**: crea `Progetti/<NomeProgetto>/Output/ETL_Documentale/`.
2. **Script canonici**: gli script Python delle Fasi 1-2 e del passo
   derivato Relazioni sono generici e riutilizzabili senza modifiche — non
   hardcodano nulla specifico di un progetto, prendono tutto da argomenti
   CLI (`--root`, `--index`, `--output`, ecc.). Se un altro progetto del
   portfolio ha già questa pipeline (es. `Progetti/Governance/Output/ETL_Documentale/`),
   copia da lì `indicizza.py`, `catalogazione.py`, `estrai_testo.py` e
   `relazioni.py` così come sono nella nuova cartella. Se nessun progetto
   del portfolio li ha ancora, chiedi all'utente da dove prenderli o scrivili
   seguendo le firme e la logica descritte in "Riferimenti agli script"
   più sotto — non serve reinventare l'algoritmo di clustering o
   l'estrazione testo per formato, è già risolto.
3. **Fase 1 — Indicizzazione** (batch, prima esecuzione):
   ```bash
   python3 indicizza.py --root "<cartella documenti del progetto>" \
       --index index_<NomeProgetto>.json --report index_<NomeProgetto>_report.md
   ```
4. **Fase 2 — Catalogazione** (batch, prima esecuzione):
   ```bash
   python3 catalogazione.py --index index_<NomeProgetto>.json \
       --root "<stessa cartella documenti>" \
       --output catalogo_<NomeProgetto>.json --report catalogo_<NomeProgetto>_report.md \
       [--label-prefix "<NomeProgetto> - "]
   ```
5. **Revisione umana del catalogo, con l'utente**: il catalogo nasce con
   `tipo: null` su ogni cluster. Presenta all'utente l'elenco dei cluster
   (etichetta, dimensione, documento rappresentativo) e chiedi di
   classificare ciascuno come `"avanzamento"` (SAL/riunioni con decisioni,
   partecipanti, action item) o `"contenuto"` (documenti tematici,
   procedure, normative, formazione) — questa distinzione guida tutto lo
   schema di Estrazione a valle, non improvvisarla da solo se il documento
   rappresentativo è ambiguo.
6. **Scegli un pilota**: non lanciarti su tutti i cluster in un colpo.
   Proponi all'utente un pilota di 2-4 cluster rappresentativi (idealmente
   almeno un cluster `avanzamento` e un paio di `contenuto`) per validare
   l'intero flusso Estrazione → Knowledge Layer → Cronistoria → Relazioni
   prima di scalare al resto — è il pattern già seguito con successo su
   Governance (pilota su cluster 1+2+21, poi esteso). Una volta scelto il
   pilota, prosegui con la Modalità B trattando quei cluster come "nuovi
   documenti da processare".

## Modalità B — Estensione incrementale

Punto di partenza: hai già (dal Passo 0) l'elenco dei documenti/cluster non
coperti o dei nuovi documenti arrivati.

### B1 — Indicizzazione e Catalogazione incrementali

Rilancia gli stessi script, ma senza toccare cluster già validati:

```bash
python3 indicizza.py --root "<cartella documenti>" --index index_<NomeProgetto>.json \
    --report index_<NomeProgetto>_report.md
```

`indicizza.py` è già pensato per essere rilanciato quante volte serve:
confronta lo stato attuale della cartella con l'indice salvato e aggiorna
solo ciò che è nuovo/cambiato/mancante, senza bisogno di flag speciali.

```bash
python3 catalogazione.py --index index_<NomeProgetto>.json --root "<cartella documenti>" \
    --catalog-in catalogo_<NomeProgetto>.json --output catalogo_<NomeProgetto>.json \
    --report catalogo_<NomeProgetto>_report.md
```

`--catalog-in` è la modalità incrementale: valuta solo i documenti nuovi o
con contenuto cambiato, li assegna ai cluster esistenti se simili abbastanza
(senza rietichettarli) o forma nuovi cluster solo con quelli non
assegnabili. Non passare `--catalog-in` se stai rifacendo tutto da zero
(refresh periodico completo) — sono due modalità deliberatamente diverse.

### B2 — Fase 3, Estrazione (lavoro di lettura/giudizio, non script)

Per i documenti nuovi/target, estrai il testo grezzo con:

```bash
python3 estrai_testo.py --root "<cartella documenti>" --paths-file elenco_percorsi.txt \
    --output testo_grezzo.json
```

(un percorso relativo per riga in `elenco_percorsi.txt`). Poi leggi
`testo_grezzo.json` e compila lo schema di Estrazione per ciascun
documento, seguendo esattamente questa struttura (coerente con
`tipo: "avanzamento"` o `"contenuto"` assegnato nel Catalogo):

```json
{
  "avanzamento": {
    "<percorso_relativo>": {
      "data_documento": "YYYY-MM-DD",
      "partecipanti": ["Nome Cognome", "..."],
      "contenuti_trattati": ["..."],
      "decisioni": ["..."],
      "rischi_blocchi": ["..."],
      "prossimi_passi": ["..."],
      "action_item": [{"responsabile": "...", "descrizione": "...", "scadenza": "..."}],
      "data_fonte": "testo" | "data_modifica_file (approssimata)" | "...",
      "parole_chiave": ["..."]
    }
  },
  "contenuto": {
    "<percorso_relativo>": {
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

`parole_chiave` è **opzionale** (aggiungilo se ha senso, non bloccare un
documento vecchio solo per popolarlo): 3-8 termini/sinonimi/varianti con
cui un utente potrebbe cercare questo documento, diversi per quanto
possibile dalle parole già in `label`/`argomento` (sigle, nomi alternativi
di un sistema, termine gergale vs termine tecnico). Serve a `etl-kb-query`
per il fallback di ricerca lessicale (Passo 3bis) quando la domanda
dell'utente non usa gli stessi termini esatti già presenti nel catalogo —
non sostituisce `argomento`/`contenuti_trattati`, che restano il riassunto
tematico principale.

Se il lotto di documenti nuovi è grande (più di ~15-20), dividilo per
cluster e lancia più subagent in parallelo, ognuno responsabile di uno o
più cluster, così da non far leggere sequenzialmente centinaia di documenti
a un solo contesto — è quello che ha permesso di estendere il pilota
Governance a 4 cluster nuovi in un'unica sessione. Se lanci più subagent in
parallelo su un lotto grande, usa il checkpoint di avanzamento descritto
sotto per non perdere il lavoro già fatto se un subagent si interrompe a
metà.

**Non inventare mai un fatto che il testo non dice esplicitamente.** Se un
documento è ambiguo (una firma di sole iniziali, una data solo nel nome
file, un ruolo generico invece di una persona), preferisci lasciare il
campo vuoto o annotarlo con un avviso (vedi B3/B4) piuttosto che
indovinare — l'inferenza va sempre segnalata, mai presentata come fatto
certo.

#### Checkpoint/resume per lotti grandi di Estrazione

Un lotto di Estrazione grande o diviso su più subagent in parallelo può
interrompersi a metà (un subagent che si blocca, un documento in un
formato che fa fallire l'estrazione del testo). Senza un checkpoint, l'unico
modo per essere sicuri di non aver perso nulla è rileggere tutto da capo —
spreco di tempo e rischio di introdurre incongruenze se una seconda lettura
interpreta un documento in modo leggermente diverso dalla prima. Mantieni
quindi un file di avanzamento accanto a `estrazione_*.json`, ad es.
`estrazione_progress.json`:

```json
{
  "in_corso": ["percorso/relativo/DocX.pptx", "..."],
  "completati": ["percorso/relativo/DocY.pptx", "..."],
  "falliti": [{"documento": "...", "errore": "..."}]
}
```

Regole pratiche:

- Prima di assegnare un documento a un subagent, controlla che non sia già
  in `completati` — se lo è, saltalo.
- Segna un documento `in_corso` quando lo assegni, e spostalo in
  `completati` solo **dopo** che la sua voce è stata scritta con successo
  in `estrazione_*.json` (o nel file temporaneo del subagent, prima del
  merge finale) — mai a inizio lettura. Così un'interruzione a metà lascia
  il documento in `in_corso` (da rifare), non erroneamente in `completati`.
- A fine lotto, se `falliti` non è vuoto, segnalalo esplicitamente
  all'utente con l'elenco e l'errore — non presentare il lotto come
  completo se non lo è.
- È un artefatto di lavoro interno alla sessione di estrazione, non fa
  parte dello schema pubblico della knowledge base: puoi cancellarlo a
  lotto completato, o lasciarlo come traccia per la prossima estensione.

### B3 — Fase 4, Knowledge Layer: fondere le nuove entità in quelle esistenti

Il Knowledge Layer normalizza persone/sistemi/normative sotto un
`nome_canonico`. Quando aggiungi documenti nuovi, per ogni entità che
incontri (persona, sistema_tool, riferimento_normativo):

1. Cerca se esiste già per `nome_canonico` (match esatto, case-insensitive)
   o per un alias già registrato, tollerando piccole varianti (es.
   "Nunzio Ferrulli" vs "Nunziangelo Ferrulli", "Aprea" da solo cognome se
   il contesto lo rende inequivocabile).
2. Se esiste: **appendi** una nuova voce a `menzioni` (non sovrascrivere le
   esistenti); se il nome incontrato è una variante, aggiungila ad `alias`
   invece di creare una seconda entità; aggiorna `ultima_menzione` solo se
   la nuova menzione ha una data `YYYY-MM-DD` esatta più recente di quella
   attuale (le date parziali/testuali non aggiornano `ultima_menzione`
   automaticamente).
3. Se non esiste: crea una nuova entità con lo schema già in uso nel
   progetto (vedi struttura sotto).
4. Ogni volta che la corrispondenza si basa su un'inferenza (solo cognome,
   identificazione via email citata in un altro documento, abbreviazione
   ambigua condivisa da più sistemi) **non risolverla in silenzio**: registra
   comunque l'entità/menzione ma annota l'inferenza nel testo di `contesto`
   e aggiungi (o estendi) una voce in `avvisi_qualita_dati` della
   Cronistoria — l'utente deciderà se confermarla. Quando l'utente conferma
   più avanti, non cancellare il ragionamento originale: aggiungi in coda
   una nota tipo `" [confermato da <Nome> il <data>]"`.

Schema di un'entità (uguale per `persone`, `sistemi_tool`,
`riferimenti_normativi`, con lievi differenze di campo — vedi
`etl-kb-query`/`references/schemas.md` se disponibile per il dettaglio
completo):

```json
{
  "id": "nome-cognome-slug",
  "tipo": "persona",
  "nome_canonico": "Nome Cognome",
  "alias": [],
  "menzioni": [
    {"documento": "...", "tipo_documento": "avanzamento|contenuto",
     "data": "...", "fonte_data": "...", "contesto": "..."}
  ],
  "ultima_menzione": null
}
```

Non serve reinventare questa logica ogni volta: scrivi (o adatta, se ne hai
già una versione da una sessione precedente) un piccolo script con queste
funzioni, e usalo invece di editare i JSON a mano voce per voce:

```python
def find_entity(kl, lista, nome_o_alias):
    """Cerca per nome_canonico o alias, case-insensitive."""
    target = nome_o_alias.strip().lower()
    for ent in kl.get(lista, []):
        if ent["nome_canonico"].strip().lower() == target:
            return ent
        if any(a.strip().lower() == target for a in ent.get("alias", [])):
            return ent
    return None

def upsert_entity(kl, lista, nome_canonico, tipo, id_slug, alias=None):
    ent = find_entity(kl, lista, nome_canonico)
    if ent is None:
        ent = {"id": id_slug, "tipo": tipo, "nome_canonico": nome_canonico,
               "alias": alias or [], "menzioni": [], "ultima_menzione": None}
        kl.setdefault(lista, []).append(ent)
    return ent

def append_menzione(ent, documento, tipo_documento, data, fonte_data, contesto):
    ent["menzioni"].append({"documento": documento, "tipo_documento": tipo_documento,
                             "data": data, "fonte_data": fonte_data, "contesto": contesto})
    # aggiorna ultima_menzione solo per date YYYY-MM-DD esatte e più recenti
    import re
    if data and re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
        attuale = (ent.get("ultima_menzione") or {}).get("data")
        if not attuale or (re.fullmatch(r"\d{4}-\d{2}-\d{2}", attuale) and data > attuale):
            ent["ultima_menzione"] = {"documento": documento, "data": data}
```

### B4 — Fase 5, Cronistoria: fondere la timeline e gli avvisi

La Cronistoria ha tre livelli, con convenzioni diverse per l'aggiornamento:

- **Timeline mecanica** (`timeline_decisioni_cluster*`): rigenerabile per
  intero dai dati (Estrazione), niente da "fondere a mano" — quando
  aggiungi documenti nuovi, ricalcola tutta la lista ordinandola per data:
  le voci con data `YYYY-MM-DD` esatta e comparabile vanno in ordine
  cronologico crescente; le voci con data solo testuale/descrittiva (non
  comparabile) vanno accodate in fondo, mantenendo la convenzione già
  presente nel file (non invertirla).
- **Possibili aggiornamenti/sostituzioni tra decisioni**: livello
  INTERPRETATO e curato — non rigenerarlo mai per intero. Se un nuovo
  documento fa evolvere un tema già tracciato, **estendi** la catena
  esistente (aggiungi un nuovo step `decisione_successiva`/`eseguita_in`);
  se è un tema nuovo, aggiungi una nuova voce con un livello di
  `confidenza` onesto (`bassa|media|media-alta|alta`), mai un'invenzione
  presentata come certa.
- **Avvisi qualità dati**: livello di flag — aggiungi una voce per ogni
  problema noto incontrato in questo giro (data contraddittoria, documento
  duplicato, identificazione incerta, abbreviazione ambigua, variante di
  nome, contenuto fuori perimetro) usando lo stesso schema già in uso nel
  file (alcuni progetti hanno `{"descrizione", "documenti"}`, altri
  `{"tipo", "descrizione", "documenti_coinvolti"}` — controlla quale usa
  il file che stai estendendo e resta coerente con quello, non introdurre
  un terzo schema).

Stessa logica: scrivi un piccolo script (o riadatta uno di una sessione
precedente) con queste funzioni, invece di editare i JSON a mano:

```python
import re

def is_iso_date(d):
    return bool(d) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))

def merge_timeline(timeline_esistente, nuove_voci):
    """Fonde nuove voci {documento, data, fonte_data, decisioni} nella
    timeline esistente: le date ISO comparabili vanno ordinate crescenti,
    le date non comparabili (testuali/descrittive) restano accodate in
    fondo nell'ordine in cui compaiono (convenzione già in uso)."""
    tutte = timeline_esistente + nuove_voci
    comparabili = [v for v in tutte if is_iso_date(v.get("data"))]
    non_comparabili = [v for v in tutte if not is_iso_date(v.get("data"))]
    comparabili.sort(key=lambda v: v["data"])
    return comparabili + non_comparabili

def append_avviso(cronistoria, descrizione, documenti, tipo=None):
    """Rispetta lo schema già in uso nel file: se le voci esistenti hanno
    'tipo'/'documenti_coinvolti' usa quello, altrimenti il più semplice
    'descrizione'/'documenti'."""
    voci = cronistoria.setdefault("avvisi_qualita_dati", [])
    usa_tipo = any("tipo" in v for v in voci)
    if usa_tipo:
        voci.append({"tipo": tipo or "altro", "descrizione": descrizione,
                     "documenti_coinvolti": documenti})
    else:
        voci.append({"descrizione": descrizione, "documenti": documenti})
```

### B4bis — Rileva aggiornamenti non incorporati sui temi tracciati (passo derivato, generico)

`possibili_aggiornamenti_decisioni` (B4) è un livello curato a mano: quando
un tema viene tracciato una volta, nessuno lo rilegge sistematicamente ogni
volta che arrivano nuovi documenti, quindi può restare indietro rispetto a
documenti più recenti che parlano dello stesso tema senza che nessuno se ne
accorga. `rileva_aggiornamenti_temi.py` è un piccolo script derivato,
deliberatamente generico e senza alcun hardcoding specifico di progetto
(nessun nome di tema, di ruolo o di dominio scritto nello script — tutto
viene letto dai dati JSON del progetto stesso), pensato per essere copiato
as-is su qualunque progetto del portfolio che segua questa pipeline (non
solo Data Governance).

Il meccanismo è deliberatamente a due livelli, per restare coerente con la
regola di trasparenza di questa skill (mai risolvere in silenzio
un'ambiguità): la parte mecanica e automatizzabile è "esiste un documento
più recente che tocca lo stesso tema tracciato e non risulta ancora nella
catena?"; la parte interpretativa resta sempre a chi legge l'avviso — lo
script non fonde mai nulla nella catena `decisione_precedente` /
`decisione_successiva` / `eseguita_in` in automatico.

Due modalità:

1. **Suggerimento parole chiave** (`--suggest-keywords`, non modifica
   nulla): per ogni tema di `possibili_aggiornamenti_decisioni` che non ha
   ancora un campo `parole_chiave` (opzionale, lista di stringhe, va
   aggiunto a mano dentro la singola voce del tema dopo conferma), propone
   candidati estratti con un'euristica leggera (frasi capitalizzate + parole
   frequenti, senza librerie NLP) dal testo del tema stesso. Presenta sempre
   i candidati all'utente per conferma/correzione prima di scriverli nel
   JSON — non salvarli mai in automatico senza revisione:
   ```bash
   python3 rileva_aggiornamenti_temi.py --cronistoria cronistoria_<NomeProgetto>.json --suggest-keywords
   ```
2. **Rilevazione** (default, richiede che almeno un tema abbia già
   `parole_chiave` confermate): confronta la data dell'ultima voce nota di
   ciascun tema con i documenti di Estrazione che menzionano le sue parole
   chiave; per ogni documento più recente non già segnalato, appende una
   voce in `avvisi_qualita_dati` con `tipo:
   "possibile_aggiornamento_tema_non_incorporato"` (stesso schema
   `{"tipo", "descrizione", "documenti_coinvolti", "tema"}` già in uso per
   gli altri avvisi tipizzati — non introduce un quarto livello dedicato in
   Cronistoria). Ha una deduplica integrata: rilanciarlo più volte non
   duplica avvisi già presenti per la stessa coppia tema/documento:
   ```bash
   python3 rileva_aggiornamenti_temi.py --cronistoria cronistoria_<NomeProgetto>.json \
       --estrazione estrazione_<NomeProgetto>.json --output cronistoria_<NomeProgetto>.json \
       --report report_rilevazione.md
   ```

Rilancia questo passo ad ogni estensione della pipeline (B1-B6), non solo su
richiesta esplicita — è il momento in cui arrivano i documenti nuovi che
potrebbero far scattare una segnalazione. Dopo la rilevazione, presenta
sempre gli avvisi generati all'utente (non limitarti a scriverli nel JSON e
andare avanti): è lui che decide se e come estendere la catena curata in
B4. Se un progetto non ha ancora nessun tema con `parole_chiave`, lo script
non genera nulla in modalità di rilevazione — è normale, significa che va
prima fatto il passaggio 1 su almeno un tema.

### B5 — Rilancia Relazioni (passo derivato)

`relazioni.py` è deterministico, leggero e non fa inferenza semantica: **non
serve fonderlo in modo incrementale**, rilancialo per intero ogni volta sul
perimetro corrente completo (Knowledge Layer + Estrazione aggiornati):

```bash
python3 relazioni.py --knowledge-layer knowledge_layer_<NomeProgetto>.json \
    --estrazione estrazione_<NomeProgetto>.json \
    --output relazioni_<NomeProgetto>.json --report relazioni_<NomeProgetto>_report.md
```

Gli archi vecchi non vengono cancellati in caso di contraddizione — resta
tutto tracciabile, e la regola "vince il documento più recente" si applica
in lettura, non in scrittura (stessa convenzione della Cronistoria).

### B6 — Aggiorna i report, la documentazione di progetto e l'ontology viewer

- **Report mecanici** (dump di timeline, elenchi entità/cluster): rigenera
  per intero dai JSON aggiornati — sono derivati al 100%, non c'è nulla da
  preservare a mano.
- **Report curati** (sezioni "Esempio N", narrativa di
  "Possibili aggiornamenti", prosa degli "Avvisi qualità dati"): **estendi
  solo**, non sovrascrivere mai per intero — sono scritti a mano e
  contengono giudizio editoriale che andrebbe perso. Prima di modificare un
  report esistente, fai sempre una copia di backup fuori dalla cartella di
  progetto (mai dentro la cartella deliverable) così puoi confrontare o
  tornare indietro.
- **README.md della pipeline**: aggiorna la descrizione del perimetro
  (quali cluster sono coperti, quanti documenti) e le statistiche di
  Relazioni (numero di archi per livello).
- **CLAUDE.md del progetto**: se il progetto tiene un Decision Log (tabella
  Data | Decisione | Contesto | Ragionamento | Alternative scartate),
  aggiungi una riga per l'estensione appena fatta — perimetro prima/dopo,
  conteggi principali, motivazione. È così che il prossimo che lavora sul
  progetto (umano o agente) capisce cosa è cambiato senza dover rileggere
  tutta la sessione.
- **Ontology viewer HTML** (`genera_ontology_viewer.py`, se presente nella
  cartella `ETL_Documentale` del progetto): è un passo di presentazione
  derivato, non una fase — rilancialo ogni volta che Knowledge Layer,
  Relazioni o Cronistoria cambiano, così il file HTML resta sincronizzato
  con i dati:
  ```bash
  python3 genera_ontology_viewer.py \
      --knowledge-layer knowledge_layer_<NomeProgetto>.json \
      --relazioni relazioni_<NomeProgetto>.json \
      --cronistoria cronistoria_<NomeProgetto>.json \
      --catalogo catalogo_<NomeProgetto>.json \
      --output ontology_viewer.html --titolo "<NomeProgetto> — Knowledge Base ETL Documentale"
  ```
  Legge solo i JSON già prodotti dalle fasi (nessuna logica di merge o di
  giudizio editoriale al suo interno) e produce un unico file HTML
  autosufficiente (grafo entità/relazioni navigabile + tabelle di
  Entità/Relazioni/Timeline/Aggiornamenti/Avvisi), apribile offline senza
  dipendenze esterne. Se il progetto non ha ancora questo script, copialo
  da un altro progetto del portfolio che lo ha (es. Governance) — è scritto
  per essere generico via argomenti CLI, nessun percorso o nome hardcoded.

## Trasparenza: la regola che vale in ogni fase

Non risolvere mai in silenzio un'ambiguità o un'inferenza — che sia
un'identificazione incerta di persona, una data contraddittoria, un'entità
che potrebbe essere la stessa di un'altra con nome scritto diversamente, o
un documento che sembra duplicato. Registrala comunque nei dati (con
un'annotazione che spiega il ragionamento), segnalala esplicitamente
all'utente in chat, e solo dopo la sua conferma aggiungi una nota di
conferma — senza mai cancellare il ragionamento originale. Questo vale
identicamente sia in bootstrap che in estensione: è quello che rende la
knowledge base affidabile da interrogare più avanti con `etl-kb-query`.

## Correzioni dell'utente: registro e comandi

Quando l'utente corregge o giudica la knowledge base ("Correggi: …",
"questo documento non va usato", "il cluster X è di tipo contenuto"), non
modificare a mano i JSON di fase né scrivere la correzione dentro uno
script di build: registrala in `correzioni_<Progetto>.json` con
`scripts/etl_pipeline/correzioni.py`. Sono annotazioni lette da
`etl-kb-query` (Passo 0bis), non modificano i dati di fase.

- "Correggi: …" / "Ricorda: …" → `correzioni.py add` (tipo, riferimento a
  documento/entità/tema, testo, motivo, autore). Conferma all'utente id e
  contenuto registrato.
- Se la correzione ne sostituisce una precedente → `correzioni.py
  supersede --id Cxxx --sostituita-da Cyyy` (la vecchia resta come storia).
- "Cosa ricordi di …?" → `correzioni.py find --query …`, mostra le voci
  attive con data e autore.
- "Dimentica: …" → `correzioni.py forget --id Cxxx`, solo su richiesta
  esplicita.

Se una correzione rivela un errore strutturale nei dati di fase (es. un
documento nel cluster sbagliato), registrala comunque e proponi
separatamente all'utente la rigenerazione della fase interessata.

## Riferimenti agli script canonici

Le Fasi 1-2 e il passo derivato Relazioni hanno un algoritmo stabile che
non richiede giudizio editoriale (a differenza di Estrazione/Knowledge
Layer/Cronistoria, che sono lavoro di lettura e interpretazione):

- **Fase 1 (Indicizzazione)**: scansiona una cartella, calcola un hash del
  contenuto di ogni file, e mantiene una storia di eventi
  (nuovo/aggiornato/invariato/mancante) rispetto all'indice salvato in
  precedenza. Rilanciabile quante volte serve senza flag speciali.
- **Fase 2 (Catalogazione)**: estrae il testo per formato (pptx, docx,
  xlsx, pdf, html, csv, md, txt, sql), costruisce una rappresentazione
  TF-IDF e clusterizza per similarità (agglomerativo, average-linkage,
  numero di cluster scelto dal gap più grande nella sequenza di merge).
  Ha una modalità batch (riclusterizza tutto) e una incrementale
  (`--catalog-in`, assegna solo i documenti nuovi/cambiati ai cluster
  esistenti via similarità al centroide, senza toccare le etichette già
  validate a mano).
- **Estrazione testo grezzo** (`estrai_testo.py`): utility che dumpa il
  testo di un elenco di documenti in un unico JSON, riusando gli stessi
  estrattori per formato della Catalogazione — serve a preparare il testo
  per la lettura di Fase 3 senza dover riaprire i file binari uno a uno.
- **Relazioni** (passo derivato, dopo Fase 3-4): costruisce archi tra
  entità canoniche del Knowledge Layer — Livello A (co-occorrenza
  documentale, segnale debole), Livello B1 (ruolo dichiarato
  esplicitamente nel testo), Livello B2 (responsabile generico → azione,
  da Estrazione). Deliberatamente non fa inferenza semantica (nessun
  "Livello C") per restare interamente tracciabile al testo sorgente.
- **Ontology viewer** (`genera_ontology_viewer.py`, passo di presentazione
  derivato, non una fase): legge Knowledge Layer + Relazioni + Cronistoria
  (+ opzionalmente Catalogo) e produce un unico HTML offline con grafo
  interattivo delle entità/relazioni e sezioni tabellari (Entità,
  Relazioni dichiarate B1/B2, Timeline, Possibili aggiornamenti, Avvisi
  qualità dati). Nessuna logica di merge o giudizio editoriale — è puro
  rendering dei JSON già prodotti dalle fasi precedenti.
- **Rileva aggiornamenti su temi tracciati** (`rileva_aggiornamenti_temi.py`,
  passo derivato dopo B4, vedi B4bis): lavora solo su Cronistoria +
  Estrazione, generico via CLI, nessun nome di tema/ruolo/dominio
  hardcoded — i temi e le loro `parole_chiave` vivono nei dati del
  progetto, non nello script. Ha due modalità (`--suggest-keywords` e
  rilevazione) e non fonde mai nulla nella catena curata in automatico:
  si limita a segnalare in `avvisi_qualita_dati` con `tipo:
  "possibile_aggiornamento_tema_non_incorporato"`.

Se questi script esistono già in un altro progetto del portfolio, copiali
as-is: sono scritti per essere generici (nessun percorso o nome hardcoded,
tutto passato via CLI). Se devi scriverli da zero per la prima volta in
assoluto nel portfolio, usa le funzioni Python indicate sopra (B3/B4) come
riferimento di stile e convenzioni per Fase 4-5, e chiedi all'utente
conferma sullo schema esatto prima di procedere in massa (una volta
fissato lo schema su un pilota piccolo, riapplicalo in modo identico a
tutto il resto).

Per calcolare la copertura reale di un catalogo (Passo 0), se la skill
`etl-kb-query` è installata usa direttamente il suo `scripts/locate_kb.py`.
Se non è disponibile, la logica equivalente è: per ogni cluster del
catalogo, conta quanti dei suoi documenti compaiono già come chiave in
`estrazione["avanzamento"]` o `estrazione["contenuto"]` — 0 su tutti →
`"non_coperto"`, tutti presenti → `"completo"`, altrimenti `"parziale"`.

