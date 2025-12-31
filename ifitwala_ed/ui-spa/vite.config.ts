// ifitwala_ed/ui-spa/vite.config.ts

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'

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
		emptyOutDir: true,
		manifest: true,
		rollupOptions: {
			input: path.resolve(__dirname, 'src/main.ts'),
			output: {
				entryFileNames: 'assets/[name].[hash].js',
				chunkFileNames: 'assets/[name].[hash].js',
				assetFileNames: 'assets/[name].[hash][extname]',
			}
		}
	}
})
