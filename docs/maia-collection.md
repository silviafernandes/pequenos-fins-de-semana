The Maia library source now starts from its own event listings rather than the
municipal calendar archive. It resolves the council's different event URL aliases
to one page, reads each monthly programme block independently and checks linked
programme PDFs on every collection. Known reviewed programmes are revisited even
if their link leaves the first listing page.

Monthly HTML sessions require an explicit date, start time, venue and age range
in the same section. The month and year come from the page's published calendar
metadata. A month-long agenda, opening-hour range, “Famílias” or “Geral” is not a
baby session. Multiple published start times remain separate sessions.

The Contamina PDF has graphical date headings. Its visual review is stored in
`public/data/maia-programmes.json` and bound to its exact SHA-256, parent page,
page title and date range. Collection downloads the currently linked document;
changed bytes, a replaced or removed link, changed page dates/title, or a
cancellation prevent the old review from publishing a session. No special
freshness exception is used: evidence still expires after 48 hours without a
successful recheck. New or changed PDFs appear as needing review in source health.

Reviewed on 22 November 2026: “Joaninha voa, voa”, 28 November at 11:30, ages 0–6,
Café Concerto do Fórum da Maia. Its end and entry price are unpublished and remain
unknown. The interface estimates one hour, as for other sessions. The linked
Google Form explicitly covers the festival's workshops and is not assigned as a
booking link for this performance.

The supplied Christmas-concert screenshot is retained as a review lead. It gives
6 December at 16:00 but does not establish a year or numerical admission age.
It is not converted into a dated baby session while those facts are unverified.
Forum and library coordinates come from their respective official Visit Maia
venue maps, including the named rooms within each venue.

Official sources:

- [Library events](https://www.cm-maia.pt/viver/cultura/equipamentos-culturais/biblioteca/noticias-eventos)
- [Contamina event](https://www.cm-maia.pt/viver/cultura/noticias-e-eventos/evento-12/7-edicao-contamina-festival-de-contos-da-maia)
- [Detailed programme PDF](https://www.cm-maia.pt/cmmaia/uploads/writer_file/document/15214/programa_detalhado_2026__1_.pdf)
- [Fórum da Maia](https://www.visitmaia.pt/public/produtos-turisticos/forum-da-maia)
- [Library venue](https://www.visitmaia.pt/public/produtos-turisticos/biblioteca-municipal-dr-jose-vieira-de-carvalho)
