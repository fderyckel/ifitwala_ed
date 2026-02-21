// ifitwala_ed/ui-spa/src/types/frappe-ui-shim.d.ts

declare module 'frappe-ui' {
	export const FrappeUI: any;
	export const Avatar: any;
	export const Badge: any;
	export const Button: any;
	export const Dialog: any;
	export const FeatherIcon: any;
	export const FormControl: any;
	export const LoadingIndicator: any;
	export const Spinner: any;

	export function call(method: string, params?: Record<string, any>): Promise<any>;
	export function createResource<T = any>(options: Record<string, any>): any;
	export function frappeRequest(options: Record<string, any>): Promise<any>;
	export function setConfig(key: string, value: any): void;

	export const toast: {
		(options: Record<string, any>): any;
		create(options: Record<string, any>): any;
		success(message: string, options?: Record<string, any>): any;
		error(message: string, options?: Record<string, any>): any;
		remove(id: string): void;
		removeAll(): void;
		promise<T = any>(
			promiseToResolve: Promise<T>,
			options: Record<string, any>
		): Promise<T>;
	};
}
