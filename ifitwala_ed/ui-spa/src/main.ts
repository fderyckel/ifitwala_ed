import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { FrappeUI } from 'frappe-ui'

// Tailwind entry (keep this file with @tailwind directives)
import './style.css'

createApp(App)
	.use(FrappeUI)
	.use(router)
	.mount('#app')
