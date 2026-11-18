export const IDEAS_PAGE_SIZE = 6
export const ideaTypes = [
  {value:'all',label:'Todos os tipos'},
  {value:'park',label:'Parques e jardins'},
  {value:'playground',label:'Com parque infantil'},
  {value:'aquarium',label:'Aquários'},
]
const fold = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-PT')
export function filterIdeas(items,{search='',area='all',type='all'}={}) {
  const words=fold(search).trim().split(/\s+/).filter(Boolean)
  return items.filter(item=>(area==='all'||item.area===area)
    &&(type==='all'||item.types.includes(type))
    &&words.every(word=>fold(`${item.title} ${item.place} ${item.shortDescription}`).includes(word)))
}
export function ideasPage(items,requestedPage,size=IDEAS_PAGE_SIZE) {
  const pages=Math.max(1,Math.ceil(items.length/size))
  const page=Math.min(pages,Math.max(1,Math.trunc(requestedPage)||1))
  const start=(page-1)*size
  return {page,pages,start,items:items.slice(start,start+size)}
}
