# Prompt per il rilevamento delle discordanze (un agente per gruppo di cluster)

Usato con `rileva_discordanze.py` (passi `prepara` e `unisci`). Sostituisci `<DOSSIER_DIR>`, `<OUT_DIR>` e l'elenco dei cluster.

---

Compito: individuare informazioni DISCORDANTI tra documenti dello stesso cluster in una knowledge base documentale (Progetto Data Governance Italgas). Un primo giro fatto troppo in fretta ha restituito zero discordanze: non è credibile. Fai un'analisi vera, leggendo per intero i dossier e, quando le schede sono troppo sintetiche per confrontare, anche i documenti sorgente indicati dal percorso (sempre solo quelli dello stesso cluster).

Confronta SOLO documenti dello stesso dossier (mai tra cluster). Input: `<DOSSIER_DIR>/dossier_<id>.json`. Ogni dossier: cluster, label, documenti[] ordinati per data (percorso, tipo, data, data_fonte, scheda con i fatti estratti), discordanze_gia_note[] (già rilevate: non riproporle con lo stesso tema; se una è confermata non toccarla).

METODO OBBLIGATORIO
1. Leggi tutto il dossier. Elenca gli oggetti ricorrenti: persone e ruoli, responsabili/owner di perimetri o attività, sistemi e tool, date e scadenze, numeri/soglie, decisioni, processi, perimetri dati.
2. Per ogni oggetto citato in almeno 2 documenti, confronta ciò che i documenti dicono. Scrivi l'esito in `verifiche`: coerente | evoluzione (il successivo aggiorna esplicitamente) | discordante | non_comparabile.
3. Una discordanza è: due o più documenti affermano cose INCOMPATIBILI sullo stesso oggetto (responsabile/owner, ruolo di una persona, data o scadenza, denominazione di sistema o processo, numero o soglia, decisione contraddetta senza aggiornamento esplicito, appartenenza di un dato a un perimetro). Non lo sono: evoluzioni dichiarate, versioni v1/v2/v3 della stessa bozza che cambiano per revisione, differenze di livello di dettaglio, argomenti diversi, varianti di grafia o sigle.
4. Se un dato cambia tra versioni successive della stessa presentazione senza che nessun testo lo dichiari, e l'altra versione resta in circolazione, segnalala con motivo "cambiato tra versioni, non dichiarato".
5. Non inventare: cita testo fedele a dossier o documenti. Percorso ESATTO dei documenti come nel dossier (attenzione alla normalizzazione Unicode dei caratteri accentati); data ISO se c'è, altrimenti null. Proposta = il documento più recente tra quelli in conflitto (regola: il più recente prevale), con motivazione breve; se le date non sono comparabili scegli comunque uno e dillo. Zero è un risultato valido solo se supportato dalle verifiche. Massimo 8 discordanze per cluster. Italiano, tono diretto.
5bis. Per ogni discordanza indica `natura`: "evoluzione" se il documento successivo aggiorna/sostituisce il precedente (anche senza dichiararlo, quando le date sono certe e la versione più recente è chiaramente quella corrente); "contraddizione" se i documenti sono validi nello stesso momento (date uguali, mancanti o non ordinabili, o documenti che restano entrambi in vigore) e dicono cose incompatibili. Solo le contraddizioni chiedono la conferma dell'utente; le evoluzioni finiscono nella cronistoria.
6. Errori delle schede di estrazione, o incoerenze interne a un solo documento, NON sono discordanze tra documenti: annotali nelle `verifiche` (nota) così possono essere corretti.

OUTPUT: per ogni cluster assegnato scrivi `<OUT_DIR>/risultati_<id>.json`:

```json
{"cluster":"<id>","verifiche":[{"oggetto":"...","documenti":["<percorso>"],"esito":"coerente|evoluzione|discordante|non_comparabile","nota":"1 frase"}],
 "discordanze":[{"tema":"titolo breve","categoria":"ruolo|responsabile|data|nome|decisione|sistema|altro","natura":"contraddizione|evoluzione","motivo":"perché incompatibili, 1-3 frasi",
   "affermazioni":[{"documento":"<percorso>","data":"YYYY-MM-DD|null","testo":"cosa dice"}],
   "proposta":{"documento":"<uno dei percorsi in conflitto>","motivazione":"..."}}]}
```

Verifiche richieste: almeno 8 per cluster con 10+ documenti, almeno 4 per cluster con 5-9 documenti, almeno 1 per i più piccoli. Risposta finale: una riga per cluster con numero di verifiche e di discordanze.
