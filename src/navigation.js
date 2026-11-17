// Let Waze resolve the named venue/entrance, rather than routing to a park centroid.
export function wazeUrl(place) {
  return `https://www.waze.com/ul?${new URLSearchParams({q:place.navigationQuery,navigate:'yes'})}`
}
