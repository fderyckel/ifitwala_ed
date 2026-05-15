// ifitwala_ed/ui-spa/src/lib/i18n.ts

import type { App } from 'vue'

const PLACEHOLDER_REGEX = /\{(\d+)\}/g

type TranslationArgs = Array<string | number>

function fallbackFormat(message: string, args?: TranslationArgs) {
	if (!args || !args.length) {
		return message
	}
	return message.replace(PLACEHOLDER_REGEX, (_, idx) => {
		const value = args[Number(idx)]
		return value !== undefined ? String(value) : ''
	})
}

function runtimeTranslator(message: string, args?: TranslationArgs) {
	const globalAny = window as unknown as Record<string, any>
	const frappeTranslator = typeof globalAny.frappe?.__ === 'function' ? globalAny.frappe.__ : null

	if (frappeTranslator) {
		try {
			return frappeTranslator(message, args)
		} catch (error) {
			console.warn('[i18n] translator threw, falling back to message', error)
		}
	}

	return fallbackFormat(message, args)
}

export function __(message: string, args?: TranslationArgs) {
	if (typeof window === 'undefined') {
		return fallbackFormat(message, args)
	}

	const globalAny = window as unknown as Record<string, any>
	const translator = typeof globalAny.__ === 'function' ? globalAny.__ : runtimeTranslator

	try {
		return translator(message, args)
	} catch (error) {
		console.warn('[i18n] global translator threw, using runtime translator', error)
		return runtimeTranslator(message, args)
	}
}

export function installI18nBridge(app: App) {
	if (typeof window === 'undefined') return

	const globalAny = window as unknown as Record<string, any>
	if (typeof globalAny.__ !== 'function') {
		globalAny.__ = runtimeTranslator
	}

	;(app.config.globalProperties as Record<string, unknown>).__ = globalAny.__
}
