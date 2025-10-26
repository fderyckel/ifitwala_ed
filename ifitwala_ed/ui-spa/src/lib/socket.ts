// ifitwala_ed/ui-spa/src/lib/socket.ts

import { io } from 'socket.io-client'

const { protocol, hostname, port } = window.location
const serverURL = `${protocol}//${hostname}${port ? ':' + port : ''}`

export const socket = io(serverURL, {
  path: '/socket.io',
  transports: ['websocket', 'polling'],
  withCredentials: true,
})