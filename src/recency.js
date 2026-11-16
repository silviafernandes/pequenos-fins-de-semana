// Recency is based on agenda admission, never on a refreshed source check.
export function isNewEvent(event, now = new Date()) {
  if (typeof event.addedAt !== 'string' || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(event.addedAt)) return false
  const age = +now - Date.parse(event.addedAt)
  return Number.isFinite(age) && age >= 0 && age < 7 * 86400000
}
