import { underThree } from './age.js'

export function eligibleSession(item, now = new Date()) {
  if (!underThree(item) || item.validationStatus !== 'verified') return false
  if (item.distanceWithinRadius !== true || !Number.isFinite(item.distanceKm) || item.distanceKm < 0 || item.distanceKm > 15) return false
  if (!/^\d{4}-\d{2}-\d{2}$/.test(item.date || '') || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(item.start || '')) return false
  const day = new Date(`${item.date}T12:00:00Z`).getUTCDay()
  if (day !== 0 && day !== 6) return false
  const today = new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Lisbon', year:'numeric', month:'2-digit', day:'2-digit'}).format(now)
  if (item.date < today || new Date(`${item.date}T12:00:00Z`) - now > 46 * 86400000) return false
  const evidence = item.sessionEvidence
  if (!evidence || !/^https?:\/\//.test(evidence.sourceUrl || '')) return false
  if (['date','start','end','minMonths','maxMonths','venue'].some(key => evidence[key] !== item[key])) return false
  const age = now - new Date(evidence.checkedAt)
  return Number.isFinite(age) && age >= 0 && age <= 48 * 3600000
}
