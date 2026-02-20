// ifitwala_ed/ui-spa/src/apps/portal/main.ts

import { createApp } from 'vue';
import PortalApp from './PortalApp.vue';
import router from '@/router';
import { FrappeUI, setConfig } from 'frappe-ui';
import { setupFrappeUI } from '@/resources/frappe';
import { installI18nBridge } from '@/lib/i18n';

// Tailwind entry + portal styles
import '@/style.css';
import '@/styles/app.css';

// PRODUCTION CONFIGURATION:
// Point to the current origin (web server).
// Nginx will proxy '/socket.io' requests to the internal socket server (port 9000).
setConfig('realtime', {
  url: window.location.origin,
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true,
});

async function bootstrap() {
  await setupFrappeUI();

  const app = createApp(PortalApp)
    .use(FrappeUI, {
      useSession: true,
      connectSocket: false, // We manually configured 'realtime' above
    })
    .use(router)

  installI18nBridge(app)

  await router.isReady()

  app.mount('#app')
}

bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Failed to bootstrap Ifitwala portal app:', err);
});
