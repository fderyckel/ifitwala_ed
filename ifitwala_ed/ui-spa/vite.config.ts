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
	base: '/assets/ifitwala_ed/dist/',
	build: {
		outDir: path.resolve(__dirname, '../public/dist'),
		emptyOutDir: true,
		manifest: true,
		rollupOptions: {
			input: {
				// Default SPA entry
				app: path.resolve(__dirname, 'src/main.ts'),
				// Desk student attendance tool entry
				attendance_tool: path.resolve(__dirname, 'src/desk/student_attendance_tool.ts'),
			},
			output: {
				entryFileNames: (chunk) => {
					if (chunk.name === 'attendance_tool') {
						return 'student_attendance_tool.bundle.js'
					}
					return 'assets/[name].[hash].js'
				},
				chunkFileNames: 'assets/[name].[hash].js',
				assetFileNames: (assetInfo) => {
					if (assetInfo.name && assetInfo.name.includes('attendance_tool') && assetInfo.name.endsWith('.css')) {
						return 'student_attendance_tool.bundle.css'
					}
					return 'assets/[name].[hash][extname]'
				},
			}
		}
	}
})
