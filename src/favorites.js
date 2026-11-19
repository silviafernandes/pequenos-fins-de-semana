const KEY='pfds-favorites'
export function loadFavorites(storage) {
  try {
    const value=JSON.parse((storage??globalThis.localStorage)?.getItem(KEY)||'[]')
    return Array.isArray(value)?[...new Set(value.filter(id=>typeof id==='string'&&id.length>0))]:[]
  } catch {return []}
}
export function persistFavorites(ids,storage) {
  try {(storage??globalThis.localStorage)?.setItem(KEY,JSON.stringify(ids));return true}
  catch {return false} // In-memory favourites still work with storage disabled/full.
}
