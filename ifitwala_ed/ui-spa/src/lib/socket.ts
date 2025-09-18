// ifitwala_ed/ui-spa/src/lib/socket.ts
import { io } from 'socket.io-client'

// Force protocol-relative URL so HTTP stays HTTP in tests
export const socket = io(`http://${location.hostname}:9000`, {
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true
});