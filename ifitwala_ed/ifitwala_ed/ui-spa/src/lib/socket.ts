// ifitwala_ed/ui-spa/src/lib/socket.ts

import { io } from 'socket.io-client'

// PRODUCTION CONFIGURATION:
// Connect to the same origin as the browser.
export const socket = io(window.location.origin, {
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true,
})
