import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * Page size that exactly fills the list box, so the list never scrolls:
 * Previous / Next show the next set instead.
 *
 * box:    ref to the element that holds the table
 * page:   ref with the current page number
 * reload: function(page) that loads that page using `size`
 */
export function useFitPage(box, page, reload) {
  const size = ref(10)
  let rowH = 44
  let headH = 38
  let observer
  let timer

  function rowsThatFit() {
    const el = box.value
    if (!el) return size.value
    return Math.max(3, Math.floor((el.clientHeight - headH - 2) / rowH))
  }

  // Use the real row and header heights once a page is on screen.
  function remember() {
    const el = box.value
    const row = el?.querySelector('tbody tr')
    const head = el?.querySelector('thead')
    if (row) rowH = row.getBoundingClientRect().height
    if (head) headH = head.getBoundingClientRect().height
  }

  // Keep the first record on screen when the page size changes.
  async function refit() {
    remember()
    const n = rowsThatFit()
    if (n === size.value) return
    const first = (page.value - 1) * size.value
    size.value = n
    await reload(Math.floor(first / n) + 1)
  }

  onMounted(async () => {
    size.value = rowsThatFit()
    await reload(1)
    await nextTick()
    await refit()
    observer = new ResizeObserver(() => {
      clearTimeout(timer)
      timer = setTimeout(refit, 200)
    })
    observer.observe(box.value)
  })
  onBeforeUnmount(() => {
    clearTimeout(timer)
    observer?.disconnect()
  })

  return size
}
