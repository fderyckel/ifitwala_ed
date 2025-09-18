// ifitwala_ed/ui-spa/src/lib/socket.ts
import { io } from 'socket.io-client'

// Force protocol-relative URL so HTTP stays HTTP in tests
export const socket = io(`//${location.host}`, {
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true
})
