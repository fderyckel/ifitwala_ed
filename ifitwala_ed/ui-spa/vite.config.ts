// ifitwala_ed/ui-spa/vite.config.ts

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'

const buildStamp =
	process.env.IFITWALA_UI_BUILD_ID ||
	new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)

export default defineConfig({
	plugins: [
		vue(),
		Components({
			resolvers: [IconsResolver({ prefix: false })]
		}),
		Icons({ compiler: 'vue3' })
	],
	resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
	base: '/assets/ifitwala_ed/vite/',
	build: {
		outDir: path.resolve(__dirname, '../public/vite'),
		// Keep older hashed assets available so already-cached portal chunks do not
		// request missing CSS/JS files during a fresh deploy.
		emptyOutDir: false,
		manifest: true,
		sourcemap: false,
		rollupOptions: {
			input: {
				'src/apps/portal/main.ts': path.resolve(__dirname, 'src/apps/portal/main.ts'),
				'src/apps/admissions/main.ts': path.resolve(__dirname, 'src/apps/admissions/main.ts'),
			},
			output: {
				entryFileNames: `assets/[name].${buildStamp}.[hash].js`,
				chunkFileNames: `assets/[name].${buildStamp}.[hash].js`,
				assetFileNames: `assets/[name].${buildStamp}.[hash][extname]`,
			}
		}
	}
})
