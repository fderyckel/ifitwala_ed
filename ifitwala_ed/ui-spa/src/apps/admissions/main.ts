// ifitwala_ed/ui-spa/src/apps/admissions/main.ts

import { createApp } from 'vue'
import AdmissionsApp from './AdmissionsApp.vue'
import router from '@/router/admissions'
import { FrappeUI, setConfig } from 'frappe-ui'
import { setupFrappeUI } from '@/lib/frappe'
import { installI18nBridge } from '@/lib/i18n'

// Tailwind entry + shared app styles
import '@/style.css'
import '@/styles/app.css'

setConfig('realtime', {
  url: window.location.origin,
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true,
})

async function bootstrap() {
  await setupFrappeUI()

  const app = createApp(AdmissionsApp)
    .use(FrappeUI, {
      useSession: true,
      connectSocket: false,
    })
    .use(router)

  installI18nBridge(app)

  await router.isReady()
  app.mount('#app')
}

bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Failed to bootstrap Admissions portal app:', err)
})
