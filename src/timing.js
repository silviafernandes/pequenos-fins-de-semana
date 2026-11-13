// Estimates are presentation values; the source record and evidence stay intact.
const minutes = value => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value || '')
  ? Number(value.slice(0,2))*60+Number(value.slice(3)) : null
const clock = value => `${String(Math.floor(value/60)%24).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`
export function sessionTiming(event) {
  const start = minutes(event.start)
  if (start === null) return null
  const publishedEnd = minutes(event.end)
  const estimated = publishedEnd === null
  const endMinutes = estimated ? start+60 : publishedEnd
  const day = new Date(`${event.date}T12:00:00Z`)
  day.setUTCDate(day.getUTCDate()+Math.floor(endMinutes/1440))
  return {startMinutes:start,endMinutes,end:clock(endMinutes),endDate:day.toISOString().slice(0,10),estimated}
}
export const napFriendly = event => {
  const time=sessionTiming(event)
  return !!time && time.startMinutes>=540 && time.startMinutes<=630 && time.endMinutes<=690
}
export const napClash = event => {
  const time=sessionTiming(event)
  return !!time && time.startMinutes<810 && time.endMinutes>690
}
export function timeLabel(event) {
  const time=sessionTiming(event)
  return time ? `${event.start}–${time.end}${time.estimated?' · fim estimado':''}` : 'Hora por confirmar'
}
