export const artworkKinds=['art','music','sports','festival','stories','sensory','nature']
const fold=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()
const themes=[
  ['sports',/\b(?:yoga|natacao|ginastica|desporto|desportos|sports?|danca)\b/],
  ['festival',/\b(?:festival|festivais|feira|carnaval|festa|festas|espetaculo|espetaculos|teatro|circo|events?)\b/],
  ['music',/\b(?:musica|musical|musicais|concerto|concertos|cancoes|som|sons|opera|music)\b/],
  ['art',/\b(?:arte|artes|art|pintura|pinturas|pintar|ceramica|ceramicas|desenho|colagem|azulejo|barro|artesanato|exposicao)\b/],
  ['sensory',/\b(?:sensorial|sensory|texturas|sentidos|luzes|exploracao)\b/],
  ['stories',/\b(?:historias|historia|contos|conto|livros|livro|leitura|bibliotecas?|stories|books?)\b/],
  ['nature',/\b(?:natureza|nature|outdoors?|horta|jardim|floresta|passeio)\b|\bar livre\b/],
]
export function activityArtwork(event){
  // Prefer explicit activity topics over a venue-based category such as Biblioteca.
  for(const text of [fold(event.title),fold(event.category)]){
    const found=themes.find(([,pattern])=>pattern.test(text))
    if(found)return found[0]
  }
  return 'festival'
}
