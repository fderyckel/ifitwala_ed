import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
	plugins: [vue()],
	resolve: {
		alias: { '@': path.resolve(__dirname, 'src') }
	},
	// Important: deploy under the app's assets subpath
	base: '/assets/ifitwala_ed/dist/',
	build: {
		outDir: path.resolve(__dirname, '../public/dist'),
		emptyOutDir: true,
		manifest: true
	}
	// (No dev server/proxy here; not used in production builds)
})


