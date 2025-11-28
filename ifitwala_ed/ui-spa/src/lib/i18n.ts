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

export function __(message: string, args?: TranslationArgs) {
	const globalAny = window as unknown as Record<string, any>
	const translator =
		typeof globalAny.__ === 'function'
			? globalAny.__
			: typeof globalAny.frappe?.__ === 'function'
				? globalAny.frappe.__
				: null

	if (translator) {
		try {
			return translator(message, args)
		} catch (error) {
			console.warn('[i18n] translator threw, falling back to message', error)
		}
	}

	return fallbackFormat(message, args)
}
