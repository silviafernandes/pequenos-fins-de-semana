import { sessionTiming } from './timing.js'
import { lisbonInstant } from './dates.js'
const escapeText=value=>String(value??'').replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,')
const stamp=date=>date.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z')
const encoder=new TextEncoder()
function fold(line) {
  const parts=[];let current='',length=0
  for(const char of line) {
    const size=encoder.encode(char).length
    if(length+size>75){parts.push(current);current=' ';length=1}
    current+=char;length+=size
  }
  parts.push(current)
  return parts.join('\r\n')
}
function eventRange(event) {
  const timing=sessionTiming(event)
  if(!timing)return null
  const start=lisbonInstant(event.date,event.start)
  // An assumed hour is elapsed time, even across a summer/winter clock change.
  const end=timing.estimated&&start?new Date(+start+3600000):lisbonInstant(timing.endDate,timing.end)
  if(!start||!end||end<=start)return null
  return {timing,start,end}
}
export function googleCalendarUrl(event) {
  const range=eventRange(event)
  if(!range)return null
  const {timing,start,end}=range
  const details=[
    event.description,
    event.ageText?`Idades: ${event.ageText}`:null,
    event.price?`Preço: ${event.price}`:null,
    timing.estimated?'Fim estimado: duração assumida de 1 hora.':null,
    event.bookingUrl?`Inscrição: ${event.bookingUrl}`:null,
    event.sourceUrl?`Fonte: ${event.sourceUrl}`:null,
  ].filter(Boolean).join('\n\n')
  const params=new URLSearchParams({action:'TEMPLATE',text:event.title||'',dates:`${stamp(start)}/${stamp(end)}`,ctz:'Europe/Lisbon',location:event.venue||'',details})
  return `https://calendar.google.com/calendar/render?${params}`
}
export function calendarText(event,now=new Date()) {
  const range=eventRange(event)
  if(!range)return null
  const {timing,start,end}=range
  const description=(timing.estimated?'Fim estimado: duração assumida de 1 hora. ':'')+(event.bookingUrl||event.sourceUrl||'')
  return [
    'BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Pequenos Fins de Semana//PT','CALSCALE:GREGORIAN','BEGIN:VEVENT',
    `UID:${encodeURIComponent(String(event.id||''))}@pequenos-fins-de-semana`,
    `DTSTAMP:${stamp(now)}`,`DTSTART:${stamp(start)}`,`DTEND:${stamp(end)}`,
    `SUMMARY:${escapeText(event.title)}`,`LOCATION:${escapeText(event.venue)}`,`DESCRIPTION:${escapeText(description)}`,
    'END:VEVENT','END:VCALENDAR',
  ].map(fold).join('\r\n')+'\r\n'
}
