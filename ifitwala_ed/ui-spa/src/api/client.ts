export async function api(method: string, payload?: any) {
	const csrf =
		(document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement)?.content || ''
	const res = await fetch(`/api/method/${method}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-Frappe-CSRF-Token': csrf
		},
		body: JSON.stringify(payload || {})
	})
	if (!res.ok) {
		throw new Error(`API error: ${res.status} ${await res.text()}`)
	}
	return res.json()
}
