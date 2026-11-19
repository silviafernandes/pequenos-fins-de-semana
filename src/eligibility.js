import { underThree } from './age.js'
import { validDate, todayPT } from './dates.js'

export function eligibleSession(item, now = new Date()) {
  if (!underThree(item) || item.validationStatus !== 'verified') return false
  if (item.distanceWithinRadius !== true || !Number.isFinite(item.distanceKm) || item.distanceKm < 0 || item.distanceKm > 15) return false
  if (!validDate(item.date) || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(item.start || '')) return false
  const day = new Date(`${item.date}T12:00:00Z`).getUTCDay()
  if (day !== 0 && day !== 6) return false
  const today = todayPT(now)
  if (item.date < today || new Date(`${item.date}T12:00:00Z`) - now > 46 * 86400000) return false
  const evidence = item.sessionEvidence
  if (!evidence || !/^https?:\/\//.test(evidence.sourceUrl || '')) return false
  if (['date','start','end','minMonths','maxMonths','venue'].some(key => evidence[key] !== item[key])) return false
  if (evidence.kind === 'reviewed-playlab-programme') {
    const source = 'https://docs.google.com/forms/d/e/1FAIpQLScd4N4mxUFYqP6l6kMYB6LvdyTCm4_Q5LGWyfWp5ekNYFtKSw/viewform'
    const reviewed = new Date(evidence.reviewedAt)
    const until = new Date(`${evidence.validUntil}T00:00:00Z`)
    const reviewedDay = String(evidence.reviewedAt || '').slice(0,10)
    return evidence.sourceUrl === source && item.venue === 'PlayLab Porto'
      && evidence.checkedAt === evidence.reviewedAt && Number.isFinite(+reviewed) && reviewed <= now
      && /^[a-f0-9]{64}$/.test(evidence.reviewDigest || '')
      && /^\d{4}-\d{2}-\d{2}$/.test(evidence.validUntil || '')
      && evidence.validUntil >= today && evidence.validUntil >= reviewedDay
      && until - new Date(`${reviewedDay}T00:00:00Z`) <= 45 * 86400000
      && item.date >= reviewedDay && item.date <= evidence.validUntil
  }
  const age = now - new Date(evidence.checkedAt)
  return Number.isFinite(age) && age >= 0 && age <= 48 * 3600000
}


export function eligibleOuting(item, now = new Date()) {
  if (item.validationStatus !== 'verified' || item.admission !== 'all-ages') return false
  if (item.distanceWithinRadius !== true || !Number.isFinite(item.distanceKm) || item.distanceKm < 0 || item.distanceKm > 15) return false
  if (!/^https:\/\//.test(item.sourceUrl || '') || !item.weekendHours) return false
  if (![item.validFrom,item.validUntil].every(validDate)) return false
  const today = todayPT(now)
  if (item.validUntil < today || item.validFrom > item.validUntil) return false
  const first = new Date(`${item.validFrom > today ? item.validFrom : today}T12:00:00Z`)
  const last = new Date(Math.min(+new Date(`${item.validUntil}T12:00:00Z`),+now+45*86400000))
  let weekend = false
  for (let d = new Date(first); d <= last; d.setUTCDate(d.getUTCDate()+1)) if ([0,6].includes(d.getUTCDay())) {weekend=true; break}
  const age = now - new Date(item.checkedAt)
  return weekend && Number.isFinite(age) && age >= 0 && age <= 48*3600000
}
