// ifitwala_ed/ui-spa/src/main.ts

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { FrappeUI, setConfig } from 'frappe-ui';
import { setupFrappeUI } from './lib/frappe';

// Tailwind entry + portal styles
import './style.css';
import './styles/app.css';

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

  const app = createApp(App)
    .use(FrappeUI, {
      useSession: true,
      connectSocket: false, // We manually configured 'realtime' above
    })
    .use(router)

  await router.isReady()

  app.mount('#app')
}

bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Failed to bootstrap Ifitwala portal app:', err);
});
