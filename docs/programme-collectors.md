# Knock-Knock and PlayLab programme collection

## Knock-Knock

The official calendar page stores its embedded Google Calendar inside Podia's public `data-props` rich-text component. `scripts/knockknock.py` decodes that text without executing JavaScript, finds the linked public group calendar and reads its public iCalendar subscription export.

The subscription reader is deliberately separate from the HTML crawler: Google's calendar HTML robots policy blocks crawling, whereas this integration consumes only the standard `/calendar/ical/<published-group-id>/public/basic.ics` subscription endpoint. It accepts no personal calendar IDs, private feeds, credentials, access tokens, arbitrary hosts, query strings or redirects. Other pages retain the existing robots checks. Each run obtains the calendar ID again from the organiser's official page; the ID is not guessed.

Recurring dates are expanded only within the existing 45-day collection window. Time zones, winter/summer changes, exclusions, moved instances and cancelled instances are handled by `icalendar` and `recurring-ical-events`. High-frequency recurrences, oversized feeds and all-day entries are not imported as timed activities.

Each session still needs an explicit eligible age and an exact recognised venue. The club's general 0–5 policy is never applied to a workshop. Unknown or older ages and unverified locations are listed in `calendarIssues`. iCalendar `STATUS:CONFIRMED` confirms a calendar entry, not vacancies: imported sessions remain `unverified`. Missing end times remain null, preserving the UI's existing one-hour estimate. A successfully read feed withdraws missing or cancelled sessions; failed reads do not refresh old evidence, which expires through the existing 48-hour rule.

The venue record uses the street address and map pin linked on the official contact page, not a Porto centroid.

**Live check, 18 November 2026:** the public export contained 60 event components, with no timed weekend occurrences in the next 45 days. The source now says “Calendário consultado · sem sessões futuras”. Past weekly schedules are not extended into November/December.

## PlayLab

The collector follows the weekend registration link on the official Google Sites agenda. The known short URL still maps to the previously observed full form. Replacement direct public Google Forms links are discovered from the weekend-labelled link; unfamiliar short links are recorded as changes and remain subject to the normal fetch/redirect checks.

A replacement form cannot grant session evidence unless it is linked from the current official agenda. Its public choices need complete ages, a consistent weekday and date, and an explicit year in the form title/description or in each full date. Evidence is anchored to the official agenda and records the actual form URL; the general Google Forms host is not blanket-approved. No private form endpoints or submitted responses are accessed.

When a form has no published year, the old reviewed year/window can be used only within the original bounded review. Public, explicitly dated programmes can add future sessions within the normal horizon without extending that manual review. The old screenshot correction is never applied to newly fetched choices, and old reviewed prices are not presented as current public prices.

`history.json → programmeWatch.playlab` stores a stable snapshot of agenda image references, the weekend form link, newsletter issue URLs and public form choices. Width-only image variants and volatile page scripts do not count as programme changes. New image references, replacement/removal of the form, new newsletter issues and changed choices are recorded in the bounded `programmeChanges` history. Failed reads retain the last snapshot instead of looking like deleted content.

A change remains marked “Programa alterado — por rever” in the source panel across unchanged scans, until a newer explicit manual review or a complete public form resolves it. A later inaccessible form cannot resurrect a superseded screenshot programme. Successfully removed/replaced programmes lose their old publication evidence; transient failures retain only previously checked evidence within its normal lifetime.

This detects changed image references; it does not claim to read or compare inaccessible image pixels. Image-based programme details still require review. No new programme-change Telegram messages are sent by this feature.

**Live check, 18 November 2026:** the weekend form returned HTTP 401 and required sign-in; the programme image returned HTTP 403. The eight future user-reviewed sessions retain their original 16 November evidence and 13 December expiry. They are not labelled as freshly confirmed options or available places.

## Validation

Regression tests cover real calendar structure, recurrence exceptions and cancellation, date/age/venue constraints, public endpoint restrictions, changed form binding, explicit-year rollover, review expiry, inaccessible form fallback and persistent change signals. Browser tests cover the new source messages. Local live checks use `scan()` without writing data or sending Telegram messages.
