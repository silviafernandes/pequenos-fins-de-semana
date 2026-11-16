PlayLab collection
==================

The existing daily and Friday collector checks the official newsletter, agenda and linked weekend form. Public form options are read from the activity question, with explicit age bands, dates, weekdays and start/end times. Suitable sessions are imported and reconciled without duplicates; a readable complete programme supersedes the reviewed snapshot. Availability remains unconfirmed.

Google currently requires sign-in. `public/data/playlab-programme.json` therefore holds the programme transcribed from the user's screenshot and the explicitly confirmed December correction. Its review date remains visible and is never replaced with a fictional live check. Reviewed sessions remain eligible only until the programme's stated expiry, at most 45 days after review. Past sessions and minimum ages of 3+ are excluded automatically.

The source panel reports the reviewed date, future session count and whether another review is needed. If the form becomes readable, the collector imports changes within the reviewed year and programme window. Unrecognised choices, new programme dates beyond that window, and access failures require review rather than guessing a year or repeating last month's dates.

To review a new programme, update the JSON with the exact form choices, explicit year, actual review timestamp and final programme date. Record any organiser/user-confirmed correction in `corrections`; do not silently repair ambiguous dates. The next scheduled run imports the new programme. No Google login or form submission is automated. The recorded prices apply to reviewed choices only; new public choices without confirmed prices show “Por confirmar”.

Checks: `python -m unittest discover -s tests -q`, `npm run build`, `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser`.
