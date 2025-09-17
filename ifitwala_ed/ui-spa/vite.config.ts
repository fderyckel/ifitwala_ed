import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

// Set VITE_FRAPPE_URL per site (e.g. http://site1.local:8000)
// so the proxy hits the right Frappe site in a multi-tenant bench.
const target = process.env.VITE_FRAPPE_URL || 'http://localhost:8000'

export default defineConfig({
	plugins: [vue()],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	base: '/assets/ifitwala_ed/dist/', // deploy under app's assets path
	build: {
		outDir: path.resolve(__dirname, '../public/dist'),
		emptyOutDir: true,
		manifest: true // emit .vite/manifest.json for backend integration
	},
	server: {
		port: 5173,
		strictPort: true,
		proxy: {
			'/api': {
				target,
				changeOrigin: true
			},
			'/assets': {
				target,
				changeOrigin: true
			}
		}
	}
})

