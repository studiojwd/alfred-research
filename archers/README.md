# Archers Encyclopedia Scraper

Use the scraper from the repository root:

```bash
python scrape_archers.py --all
python scrape_archers.py --characters --dry-run
python scrape_archers.py --character "Jill Archer" --update-existing
python scrape_archers.py --location "Brookfield Farm"
python scrape_archers.py --character "Jill Archer" --dry-run --timeout 8 --retries 1
python scrape_archers.py --character "Jill Archer" --dry-run --sources wikipedia,radiotimes
python scrape_archers.py --character "Jill Archer" --sources wikipedia,radiotimes --use-llm --llm-model gpt-4o-mini
python scrape_archers.py --character "Jill Archer" --sources wikipedia,radiotimes --research-mode --llm-model gpt-4o-mini
```

The workflow reads the master character and location indexes, de-duplicates entries, queries the approved source adapters in priority order, merges the results into a normalised record, renders markdown from the supplied templates, writes or updates archive files, regenerates the master indexes, and records source notes in [`logs/research_notes.md`](/Users/jonwhitby/Desktop/biteee/alfred-research/archers/logs/research_notes.md).

Notes:

- Runtime dependencies are `requests`, `beautifulsoup4`, and `lxml`.
- Optional LLM synthesis uses the official `openai` Python SDK and `OPENAI_API_KEY`.
- Install them with `python3 -m pip install requests beautifulsoup4 lxml openai`.
- Use `--dry-run` before a full run if you want to inspect planned writes.
- Use `--update-existing` to merge generated sections back into existing files while preserving human-written notes where possible.
- Use `--create-missing-only` to avoid touching existing archive pages.
- If a source is consistently failing in your network environment, lower `--timeout` and `--retries`; the scraper will now disable that source for the rest of the run after repeated failures.
- Use `--sources` or `--skip-sources` to restrict a run to the domains that actually respond from your machine.
- Use `--use-llm` to let a model synthesise extra fields from the fetched source snippets. This is optional and should be treated as a normalisation layer over approved-source extracts, not an independent source of facts.
- Use `--research-mode` as a clearer single-item/small-batch flag for LLM-assisted enrichment on matched pages.
- Existing richer pages are now protected against downgrade: if a later run produces a weaker fallback page, the scraper will preserve the better existing file.
- If `family_tree.json` exists at the repo root, the scraper will refresh it from the generated relationship fields.
