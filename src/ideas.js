import { normalizeSearch as fold } from './search.js'
export const IDEAS_PAGE_SIZE = 6
export const ideaTypes = [
  {value:'all',label:'Todos os tipos'},
  {value:'park',label:'Parques e jardins'},
  {value:'playground',label:'Com parque infantil'},
  {value:'indoor-play',label:'Brincar no interior'},
  {value:'aquarium',label:'Aquários'},
]
export const amenityDefinitions=[
  {key:'playground',label:'Parque infantil'},
  {key:'toilets',label:'WC'},
  {key:'cafe',label:'Café/bar'},
  {key:'changingTable',label:'Fraldário'},
  {key:'strollerAccess',label:'Acesso com carrinho'},
]
export function hasAmenity(item,key){return item.amenities?.[key]?.status==='confirmed'}
export function amenitySummary(item){
  if(hasAmenity(item,'playground')){
    const p=item.amenities.playground
    const label=item.types.includes('indoor-play')?'Parque interior':'Parque infantil'
    return `${label} · ${Number.isFinite(p.minMonths)?p.ageText:'idades por confirmar'}`
  }
  const known=amenityDefinitions.filter(a=>hasAmenity(item,a.key)).map(a=>a.label)
  return known.length?known.slice(0,2).join(' · '):'Instalações por confirmar'
}
export function amenityLabel(fact){
  if(!fact||fact.status==='unknown')return 'Por confirmar'
  if(fact.status==='temporarily-closed')return 'Encerrado provisoriamente na fonte'
  return fact.ageText||'Confirmado na fonte'
}
const amenitySearchText=item=>amenityDefinitions.filter(a=>['confirmed','temporarily-closed'].includes(item.amenities?.[a.key]?.status)).map(a=>`${a.label} ${item.amenities[a.key].ageText||''}`).join(' ')

export function filterIdeas(items,{search='',area='all',type='all'}={}) {
  const words=fold(search).trim().split(/\s+/).filter(Boolean)
  return items.filter(item=>(area==='all'||item.area===area)
    &&(type==='all'||(type==='playground'?hasAmenity(item,'playground'):item.types.includes(type)))
    &&words.every(word=>fold(`${item.title} ${item.place} ${item.shortDescription} ${amenitySummary(item)} ${amenitySearchText(item)}`).includes(word)))
}
export function ideasPage(items,requestedPage,size=IDEAS_PAGE_SIZE) {
  const pages=Math.max(1,Math.ceil(items.length/size))
  const page=Math.min(pages,Math.max(1,Math.trunc(requestedPage)||1))
  const start=(page-1)*size
  return {page,pages,start,items:items.slice(start,start+size)}
}
