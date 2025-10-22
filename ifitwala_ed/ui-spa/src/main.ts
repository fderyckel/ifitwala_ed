import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { FrappeUI, setConfig } from 'frappe-ui'
import './lib/socket.ts'
import { setupFrappeUI } from './resources/frappe'

// Tailwind entry (keep this file with @tailwind directives)
import './style.css'

// tell frappe-ui where to connect for realtime
setConfig('realtime', {
  url: window.location.origin,
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true,
})

async function bootstrap() {
  await setupFrappeUI()

  createApp(App)
    .use(FrappeUI)
    .use(router)
    .mount('#app')
}

bootstrap()
