// ui-spa/src/main.ts

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { FrappeUI, setConfig } from 'frappe-ui';
import { setupFrappeUI } from './lib/frappe';

// Tailwind entry + portal styles
import './style.css';
import './styles/app.css';

// Configure real‑time to use your bench’s socket.io server.
// Frappe’s default socket server runs on port 9000 and uses HTTP.
const socketProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socketHost = window.location.hostname;
setConfig('realtime', {
  // e.g. ws://34.61.243.240:9000
  url: `${socketProtocol}//${socketHost}:9000`,
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true,
});


async function bootstrap() {
  await setupFrappeUI();

  const app = createApp(App)
    .use(FrappeUI, {
      useSession: true,
      connectSocket: false,
    })
    .use(router)

  await router.isReady()

  app.mount('#app')
}


bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Failed to bootstrap Ifitwala portal app:', err);
});
