const record = value => value!==null&&typeof value==='object'&&!Array.isArray(value)
const records = value => Array.isArray(value)&&value.every(record)
const validators = {
  data:value=>record(value)&&records(value.events)&&(value.outings===undefined||records(value.outings)),
  history:value=>record(value)&&(value.observations===undefined||records(value.observations)),
  discoveries:value=>record(value)&&record(value.sourceIndex)&&Object.values(value.sourceIndex).every(record),
}
// Apply each feed as it succeeds: an unavailable optional source report must
// not hold back the activity data or replace a last-good report with a seed.
export async function refreshFeeds(urls,handlers,{fetcher=globalThis.fetch,signal}={}) {
  const results=await Promise.allSettled(Object.entries(urls).map(async([key,url])=>{
    const response=await fetcher(url,{cache:'no-store',signal})
    if(!response.ok)throw Error(`Unable to update ${key}`)
    const value=await response.json()
    if(!validators[key](value))throw Error(`Invalid ${key} payload`)
    if(!signal?.aborted)handlers[key](value)
  }))
  return results.every(result=>result.status==='fulfilled')
}
