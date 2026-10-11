// Search while typing: run `fn` a moment after the last key press, so a fast typist
// does not send one request per letter. Call `now()` (e.g. on Enter) to search at once.
import { onBeforeUnmount } from 'vue'

export function useLiveSearch(fn, delay = 250) {
  let timer = null
  const now = () => { clearTimeout(timer); timer = null; fn() }
  const soon = () => { clearTimeout(timer); timer = setTimeout(now, delay) }
  onBeforeUnmount(() => clearTimeout(timer))
  return { soon, now }
}

// Wraps an async loader so only the answer to the latest call is used
// (an older, slower answer must not replace a newer one).
export function latestOnly(loader) {
  let n = 0
  return async (...args) => {
    const mine = ++n
    const r = await loader(...args)
    return mine === n ? r : undefined
  }
}
