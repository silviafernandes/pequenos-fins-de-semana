# Collection audit — 18 November 2026

## Is it running?

Yes: the latest production run, [44297708231](https://github.com/silviafernandes/pequenos-fins-de-semana/actions/runs/44297708231), completed successfully at 11:49 Lisbon time. Its collection snapshot was 11:48:48. All 20 source entry pages were reached, with 25 published sessions, eight pending records and two collected opening-hour outings. The run found no new sessions, which does not establish that no uncollected events exist.

The ten most recent scheduled runs returned by GitHub all succeeded. A daily 09:13 Lisbon scan and extra Friday scans are configured. Actual scheduled execution has been much later than configured: the 17 November run started at 18:30, and the 16 November run at 19:32. Today's morning updates came from code pushes; a punctual scheduled morning run is not established. GitHub scheduling is not suitable for a guarantee of exact-time booking alerts.

## What “sources OK” hid

- Porto libraries parsed two known PAPI sessions but 11 selected detail URLs returned 404. The HTML document has a root `<base href>` which the collector ignored, creating `/programa/evento/...` instead of `/evento/...`. Link resolution now respects valid HTTP(S) document bases. Serralves uses the same pattern.
- Maia's library source pointed at the municipal homepage and yielded no relevant links. It now points directly at the municipal agenda, which links the current monthly library programme.
- PlayLab's public programme/form check still requires manual review when sign-in blocks the form. Previously reviewed sessions retain their original bounded evidence; a successful newsletter fetch is not a live confirmation of changes or vacancies.
- Knock-Knock's calendar returned a page but no sessions or relevant links. Guli and Gaia also yielded no sessions in the production snapshot; independent rechecks returned HTTP 403. Access and content coverage must be kept separate.
- Pumpkin and Pequenos Planos have more candidate links than the bounded per-run budget. Pages rotate across runs; the scan is explicitly partial. Generic family links can lead to editorial or older content rather than a confirmed baby event.
- Matosinhos Google Forms short links could not be checked because robots.txt returned HTTP 400. Poster candidates also await review. These errors were present despite the entry page being reachable.
- Tesseract was configured to emit both plain text and TSV. That contaminated some stored poster review text. OCR now requests TSV alone; OCR proposals still cannot publish a session without review.

## Coverage added

Three public official sources were checked successfully, including the collector's robots policy, and added to the watchlist:

| Source | Coverage and limits |
| --- | --- |
| [Serralves](https://www.serralves.pt/agenda-serralves/) | Family workshops, nature and seasonal markets. Free child admission is not evidence of a workshop's minimum age. |
| [Museu do Porto](https://museudoporto.pt/agenda/) | Museum workshops and educational programmes. Family titles alone do not establish under-three suitability. |
| [MHNC-UP](https://mhnc.up.pt/pt/eventos/index.php) and its [family programme](https://mhnc.up.pt/pt/servico-educativo/familias/) | Natural History and Science Museum, Biodiversity Gallery and Botanical Garden. Each activity needs its exact venue, age and session details. |

These are monitored discovery sources, not a claim of complete automatic extraction. The generic collector reads structured events and official adapters; unstructured pages still need an adapter or review. Event path slugs now make image-only and “Ver mais” family workshop links discoverable. No new minimum ages, dates, locations or availability are inferred.

Useful next candidates are Teatro Municipal do Porto and Teatro Nacional São João (both returned 403 in the independent check), plus Planetário do Porto and Pavilhão da Água (pages accessible, but under-three session eligibility still needs checking). Existing zoo and Christmas sources should be completed before adding duplicate aggregator feeds.

## Ongoing diagnostics

Every source now has `collectionHealth`: `collected`, `partial`, `review-needed`, `discovery-only`, `no-sessions`, or `unavailable`, with reasons. `ok` continues to mean only that the source entry point was reached. The collector prints health counts and adds a per-source coverage table to the GitHub Actions summary. The website source panel explicitly reports extracted sessions or links without extracted sessions.

Publication still requires the existing age, weekend, date, exact-location/radius and source-evidence checks. Page access, general family admission, and available registration links do not prove available places.
