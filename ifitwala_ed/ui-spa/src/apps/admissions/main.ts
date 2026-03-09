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

const ADMISSIONS_CHUNK_RELOAD_FLAG = 'ifitwala:admissions:chunk-reload'

function isChunkLoadError(err: unknown): boolean {
  const message = err instanceof Error ? err.message : String(err || '')
  if (!message) return false
  const normalized = message.toLowerCase()
  return (
    normalized.includes('failed to fetch dynamically imported module') ||
    normalized.includes('importing a module script failed') ||
    normalized.includes('error loading dynamically imported module')
  )
}

function getChunkReloadFlag(): boolean {
  try {
    return window.sessionStorage.getItem(ADMISSIONS_CHUNK_RELOAD_FLAG) === '1'
  } catch {
    return false
  }
}

function setChunkReloadFlag(enabled: boolean) {
  try {
    if (enabled) {
      window.sessionStorage.setItem(ADMISSIONS_CHUNK_RELOAD_FLAG, '1')
      return
    }
    window.sessionStorage.removeItem(ADMISSIONS_CHUNK_RELOAD_FLAG)
  } catch {
    // Best effort only. If storage is unavailable, skip persistence.
  }
}

function installChunkLoadRecovery() {
  router.onError((err, to) => {
    if (!isChunkLoadError(err)) return

    if (getChunkReloadFlag()) {
      setChunkReloadFlag(false)
      // eslint-disable-next-line no-console
      console.error('Admissions chunk load failed after one recovery reload.', err)
      return
    }

    setChunkReloadFlag(true)
    const target = to?.fullPath || `${window.location.pathname}${window.location.search}${window.location.hash}`
    window.location.assign(target)
  })

  router.afterEach(() => {
    setChunkReloadFlag(false)
  })
}

async function bootstrap() {
  await setupFrappeUI()
  installChunkLoadRecovery()

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
