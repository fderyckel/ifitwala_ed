import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import Icons from 'unplugin-icons/vite'
import Components from 'unplugin-vue-components/vite'
import { IconsResolver } from 'unplugin-icons/resolver'

export default defineConfig({
	plugins: [
		vue(),
		Components({
			resolvers: [IconsResolver({ prefix: false })]
		}),
		Icons({
			compiler: 'vue3'
			// optional: autoInstall: true  // only if your CI has network access
		})
	],
	resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
	base: '/assets/ifitwala_ed/dist/',
	build: {
		outDir: path.resolve(__dirname, '../public/dist'),
		emptyOutDir: true,
		manifest: true
	}
})


