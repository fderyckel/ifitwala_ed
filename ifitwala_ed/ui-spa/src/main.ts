// ui-spa/src/main.ts

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { FrappeUI, setConfig } from 'frappe-ui';
import { setupFrappeUI } from './resources/frappe';

// Tailwind entry + portal styles
import './style.css';


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
  // Set fetchOptions and CSRF token
  await setupFrappeUI();

  createApp(App)
    .use(FrappeUI, {
      // Tell Frappe‑UI to send the sid cookie on every call
      useSession: true,
      // Disable auto‑connecting the socket on the portal; the student/staff
      // portal doesn’t need real‑time events
      connectSocket: false,
    })
    .use(router)
    .mount('#app');
}

bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Failed to bootstrap Ifitwala portal app:', err);
});
