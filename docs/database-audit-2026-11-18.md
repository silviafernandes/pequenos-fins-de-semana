Database audit — 18 November 2026
================================

The audit covers all 14 year-round places, all published and pending event records, the two collected opening-hour outings, and the nine venue records. The activity snapshot reviewed initially contained 25 published sessions and eight pending records. Different start times on the same programme page are separate sessions; none were duplicate sessions.

Place corrections
-----------------

Eight missing playground tags were confirmed, bringing the total from two to ten. Evidence is stored per facility in `src/evergreenIdeas.json`, with its source, specific supporting text and review date. Every place has an explicit state for playground, WC, café/bar, baby changing and stroller access. Unconfirmed is not the same as absent. Playground presence does not establish suitability for under-threes.

| Place | Playground | Published equipment ages / qualification |
| --- | --- | --- |
| Quinta da Conceição | Confirmed | Municipal register: 6–12 years |
| Parque do Carriçal | Confirmed | Municipal register: 3–12 years |
| Parque das Varas | Confirmed | Municipal register: 3–12 years |
| Jardim Basílio Teles | Confirmed | Municipal register: 3–12 years |
| SEA LIFE Porto | Confirmed | Official FAQ: under 9; minimum not published; aquarium admission is paid |
| Parque Infantil do Covelo | Confirmed | Equipment age limits not confirmed |
| Parque da Cidade | Unconfirmed | A missing mention on the park page is not evidence of absence |
| Jardins do Palácio de Cristal | Confirmed | Equipment age limits not confirmed |
| Jardim do Passeio Alegre | Unconfirmed | Mini-golf is not automatically classified as a playground |
| Parque Público de São Mamede | Confirmed | Municipal register: 3–5 years, Rua da Igreja Velha |
| Jardins da Quinta de Santiago | Unconfirmed | Not confused with the unrelated Parque Infantil de Santiago in Custóias |
| Parque de São Roque | Confirmed | Municipal playground page, Travessa das Antas |
| Parque da Pasteleira | Confirmed | Equipment age limits not confirmed |
| Jardim Botânico do Porto | Unconfirmed | General garden information does not establish a playground |

The source is Matosinhos' public municipal GIS playground register for its five named playground records (objects 4154, 4214, 4136, 4171 and 4204), supplemented by official Porto park/playground pages and SEA LIFE's FAQ. The full record URLs are retained in the catalogue.

Other facilities and routing
---------------------------

- WC confirmed at six places, café/bar at six, baby changing at SEA LIFE, and stroller access at SEA LIFE.
- Pasteleira's municipal page explicitly says its café is temporarily closed. It is not shown as an available café.
- SEA LIFE says there is no storage area for strollers; the family keeps the stroller with them.
- The public São Mamede park was bound to its named municipal garden record at Rua da Igreja Velha, rather than relying on an ambiguous development-plan page.
- São Roque's Waze destination now uses its municipal playground entrance on Travessa das Antas.
- Toilets in a neighbouring building, a named e-learning café, generic wheelchair accessibility, or a school playground do not automatically establish a visitor facility in the listed park.

Event corrections
-----------------

- The eight Casa da Música sessions explicitly name Sala Ensaio 2. The collector now records indoors and the official purchase-interface page as the booking destination, with evidence. It does not infer available places.
- The two PAPI sessions explicitly name the Almeida Garrett auditorium. The collector now records indoors, free admission, the published 20-child capacity and the requirement to collect a ticket at the library information desk. Capacity is not remaining availability.
- Nine end times were not published in the reviewed snapshot. These remain unknown in source data; the existing UI-only one-hour estimate is retained.
- Prices, source receipts, venue-level geography, ages and registration links were checked for missing fields across published records. Missing booking URLs are not invented where registration happens at a counter or no public booking URL is established.
- Pending records remain unpublished unless the normal date, age, location and source checks pass. PlayLab's user-reviewed programme retains its original review date and bounded validity; its sign-in wall is not bypassed.

Checks and future maintenance
-----------------------------

Run `python scripts/audit_database.py` for a read-only completeness report, including unknown event fields and source-evidence errors. Unknown fields are reported, not fabricated. New catalogue tests reject facility claims without evidence and playground tags that disagree with the structured facility record. Browser checks cover the corrected playground filter, age disclosure, compact cards and existing pagination/navigation behaviour.

This is a source audit, not a physical inspection or a guarantee that every facility is open at the moment of arrival. Each record keeps its own review date and public source.
