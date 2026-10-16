import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

// The screens are laid out for a laptop. On a monitor wider than BASE_WIDTH the whole
// app is enlarged in step with the screen, so text and controls grow and no side is left empty.
// --vh is the real screen height in the app's own (enlarged) units; the styles use it instead of 100vh.
const BASE_WIDTH = 1600 // a 1920-wide monitor is enlarged 1.2 times; raise this number for smaller text
function fitToScreen() {
  const root = document.documentElement
  const printing = location.pathname.startsWith('/print') // receipts, cards and labels keep their real size
  const zoom = printing ? 1 : Math.min(2, Math.max(1, window.innerWidth / BASE_WIDTH))
  root.style.zoom = zoom === 1 ? '' : String(zoom)
  root.style.setProperty('--vh', window.innerHeight / zoom + 'px')
}
fitToScreen()
window.addEventListener('resize', fitToScreen)

createApp(App).use(router).mount('#app')
