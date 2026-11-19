# Code review — 19 November 2026

Scope: activity eligibility and collection, PlayLab updates, React loading/state, calendar export, search and GitHub Actions publication. The fixes below preserve the under-three, exact-venue/radius and source-evidence requirements.

## Findings and fixes

| Priority | Finding and concrete trigger | Resulting fix |
| --- | --- | --- |
| High | `App` loaded three JSON feeds with one `Promise.all`. A network failure fetching optional history/source diagnostics discarded a successful activity refresh. Malformed primary responses could also reach rendering. | Feeds apply independently after basic shape validation. Failed requests preserve last-good data. Initial missing diagnostics use neutral wording rather than incorrectly saying collection has not started. Requests have a timeout, abort on unmount and do not overlap; returning to the tab retries them. |
| High | Session eligibility was memoized without a clock dependency, and the six-weekend window was memoized once. An open tab could retain expired evidence during failed refreshes and keep the previous week's dates after Monday. | A minute clock and visibility refresh update eligibility, registration badges, recency and weekend dates. An obsolete weekend selection resets to “Todos”. |
| Medium | Favourites accepted any parsed JSON. Valid JSON such as `null` or `{}` caused `.includes` failures. A quota/privacy error during `setItem` could break the click handler. | Favourites load only unique string IDs; reads/writes are guarded. Favourites remain usable in memory when storage is unavailable. |
| Medium | Calendar TEXT fields escaped commas only. Semicolons, backslashes and line breaks in an imported title/venue could corrupt the file. Long UTF-8 lines were not folded, and local TZID-only times relied on each calendar client's timezone support. | A pure exporter escapes TEXT and folds physical lines at 75 UTF-8 bytes. Start/end are exported as UTC instants derived from Lisbon time. Unknown ends still mean one elapsed hour, including clock changes, without altering source records. |
| Medium | JavaScript normalized impossible dates such as 29 February 2026 into a real Sunday. Upper age bounds were not required in the browser, while Python accepted booleans/non-finite numbers as numeric ages. | Real calendar dates and finite, ordered age bounds are checked. Python eligibility and the publication audit share the age-range check. JSON output rejects non-standard `NaN`/`Infinity` rather than publishing an unreadable feed. |
| Medium | Complete public PlayLab form choices incremented `liveSessions` but left the source's generic `parsedSessions` at zero. The source panel could say no sessions were extracted while importing one. | The source's extracted-session count includes its live form result. A regression follows a replacement public form through the full scan and checks both the count and collection health. |
| Medium | Every UI-only push waited for OCR installation and a full external crawl. A UI commit arriving during collection could reject the bot's data push; a later build could use old data/code. Simply checking the latest push also misses an intermediate collector change when queued jobs are replaced. | UI-only pushes reuse checked data when it is under 24 hours old and matches the current collector/settings and generated data. Scheduled/manual runs always scan. Missing, edited or stale metadata forces a scan. Bot data commits rebase onto concurrent code commits without force-pushing, and the latest main snapshot is checked before building. Mismatched inputs or conflicting manual data edits stop publication rather than publish a mixed snapshot. |
| Low | Activity search kept accents while place search folded them, and activity category names were absent from the text search. | Both searches share normalization; “musica” matches “Música”, and activity categories are searchable. |

Date, calendar, feed, favourites and search logic now live in small modules with focused unit tests. Unused presentation helpers and icon imports were removed from `App.jsx`.

## Validation

- 124 Python tests and 9 JavaScript unit tests passed.
- Production build and browser regressions passed, including failed optional feeds, invalid favourites plus unavailable storage, live evidence expiry, Monday rollover, filters, pagination, source disclosures and mobile overflow.
- An independent `icalendar` parser round-tripped punctuation, backslashes and newlines as one event. A summer 10:00 Lisbon activity imported as 09:00 UTC with a one-hour duration.
- A local bare-Git simulation preserved a concurrent UI update and the collector's fresh data through rebase/push.
- Collection-cache regressions cover intermediate source changes, manual data edits, missing metadata and data over 24 hours old. These prevent the UI fast path from skipping required processing.
- The full local collection completed: 24 of 25 source entry points were reached; Casa da Arquitetura returned HTTP 403 and remained reported as unavailable. Checked-data consistency passed and the database audit reported no errors. Telegram sending was disabled.

## Operational boundaries

Normal source checks still require published age, date/time and venue evidence; unknown information remains pending. A private PlayLab form and unstructured programme images still require review. GitHub's scheduled start time remains subject to platform delays.

Conflicting concurrent edits to generated data deliberately stop the older publication instead of overwriting the edit. A newer run processes the latest inputs. Calendar sources containing only a repeated autumn wall-clock time cannot distinguish the two occurrences; UTC conversion consistently uses the first occurrence, while an estimated duration remains one elapsed hour. Non-existent spring times are not exported.
