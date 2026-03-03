// ifitwala_ed/ui-spa/src/types/vitest-config-shim.d.ts

declare module 'vitest/config' {
	export function defineConfig<T = any>(config: T): T;
}
