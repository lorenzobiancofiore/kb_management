# kb_management

Script e skill per la pipeline ETL documentale a 5 fasi (Indicizzazione → Catalogazione →
Estrazione → Knowledge Layer → Cronistoria) usata per costruire e interrogare knowledge base
di progetto (es. `Output/ETL_Documentale` dentro i progetti Bludigit).

I dati dei singoli progetti (catalogo, estrazione, knowledge layer, cronistoria, report) NON
sono in questo repo: restano nella cartella del progetto (es. `Progetti/Governance/Output/`).
Questo repo contiene solo il codice che li genera/legge.

## Struttura

- `scripts/etl_pipeline/` — costruzione della KB: indicizzazione, catalogazione, estrazione
  knowledge layer, cronistoria, merge e aggiunta di nuovi documenti a una pipeline esistente.
- `scripts/reports/` — generazione/aggiornamento dei report leggibili (HTML/MD) da KL e
  Cronistoria.
- `scripts/analysis/` — strumenti derivati: rilevamento aggiornamenti su temi tracciati,
  ontology viewer HTML, benchmark della skill `etl-kb-query`, utility di correzione date.
- `skills/etl-kb-build/` — skill Claude per costruire/estendere la pipeline (SKILL.md).
- `skills/etl-kb-query/` — skill Claude per interrogare una KB già costruita, incluso il
  fallback lessicale TF-IDF (`scripts/semantic_candidates.py`) per domande ampie/multi-tema.

## Note

- Gli script si aspettano in input un path a `Output/ETL_Documentale` del progetto (passato
  come argomento, es. `--etl-dir`).
- Le skill vanno installate/aggiornate in Claude tramite il meccanismo di packaging (`.skill`)
  descritto nei rispettivi `SKILL.md`.
