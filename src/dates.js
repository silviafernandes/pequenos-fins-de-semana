// Calendar arithmetic uses dates at UTC noon; user-facing days use Lisbon.
const dateFormat = new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Lisbon',year:'numeric',month:'2-digit',day:'2-digit'})
const partsFormat = new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/Lisbon',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'})
export const todayPT = (now = new Date()) => dateFormat.format(now)
export function lisbonDateTime(now) {
  const p=Object.fromEntries(partsFormat.formatToParts(now).map(x=>[x.type,x.value]))
  return {date:`${p.year}-${p.month}-${p.day}`,time:`${p.hour}:${p.minute}`}
}
export const datePlusDays = (date,days) => {
  const value = new Date(`${date}T12:00:00Z`)
  value.setUTCDate(value.getUTCDate()+days)
  return value.toISOString().slice(0,10)
}
export function nextSixWeekends(now = new Date()) {
  const today=todayPT(now), day=new Date(`${today}T12:00:00Z`).getUTCDay()
  const saturday=datePlusDays(today,day===0?-1:(6-day+7)%7)
  return Array.from({length:6},(_,i)=>datePlusDays(saturday,i*7))
}
export function validDate(value) {
  return typeof value==='string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(`${value}T12:00:00Z`))
    && new Date(`${value}T12:00:00Z`).toISOString().slice(0,10)===value
}
export function lisbonInstant(date,time) {
  if(!validDate(date)||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time||''))return null
  const naive=Date.parse(`${date}T${time}:00Z`)
  // Portugal's present-day offsets are UTC and UTC+1. Round-trip both instead
  // of assuming that the offset at noon applies before a clock change.
  for(const offset of [60,0]) {
    const candidate=new Date(naive-offset*60000)
    const local=lisbonDateTime(candidate)
    if(local.date===date&&local.time===time)return candidate
  }
  return null // A non-existent spring-clock time must not be silently shifted.
}
export function openingInstant(stamp) {
  if(typeof stamp!=='string'||!validDate(stamp.slice(0,10)))return null
  if(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(stamp))return lisbonInstant(stamp.slice(0,10),stamp.slice(11))
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/.test(stamp))return null
  const parsed=new Date(stamp)
  return Number.isFinite(+parsed)?parsed:null
}
export function openingThisWeek(event,now=new Date()) {
  const opening=openingInstant(event.openingAt)
  if(event.status!=='scheduled'||!opening||opening<=now)return false
  const today=todayPT(now), day=new Date(`${today}T12:00:00Z`).getUTCDay()
  return todayPT(opening)<datePlusDays(today,7-((day+6)%7))
}
