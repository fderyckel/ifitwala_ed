// ifitwala_ed/ui-spa/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver' // ✅ default import

export default defineConfig({
	plugins: [
		vue(),
		Components({
			resolvers: [IconsResolver({ prefix: false })]
		}),
		Icons({ compiler: 'vue3' })
	],
	resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
	base: '/assets/ifitwala_ed/dist/',
	build: {
		outDir: path.resolve(__dirname, '../public/dist'),
		emptyOutDir: true,
		manifest: true
	}
})


