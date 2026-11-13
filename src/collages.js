export const collages = [
  {id:'bird',name:'Passarinho',file:'header-paper-bird.webp'},
  {id:'city',name:'Casas',file:'header-paper-city.webp'},
  {id:'butterfly',name:'Borboleta',file:'header-paper-butterfly.webp'},
  {id:'music',name:'Música',file:'header-paper-music.webp'},
]

export function nextCollage(current,random=Math.random) {
  if (!Number.isInteger(current) || current<0 || current>=collages.length) return Math.floor(random()*collages.length)
  const choice=Math.floor(random()*(collages.length-1))
  return choice>=current ? choice+1 : choice
}
