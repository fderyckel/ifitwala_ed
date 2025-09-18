import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { FrappeUI } from 'frappe-ui'
import './lib/socket.ts'

// Tailwind entry (keep this file with @tailwind directives)
import './style.css'

// --- ensure socket.io uses the same origin & HTTP when you're on HTTP ---
import { setConfig } from 'frappe-ui'

// tell frappe-ui where to connect for realtime
setConfig('realtime', {
  // use the exact origin you're loaded from: http://35.238.92.31
  url: window.location.origin,
  // nginx proxies this path to the node socketio server
  path: '/socket.io',
  // prefer websocket; allow polling as fallback (optional)
  transports: ['websocket', 'polling'],
  withCredentials: true,
})

createApp(App)
	.use(FrappeUI)
	.use(router)
	.mount('#app')