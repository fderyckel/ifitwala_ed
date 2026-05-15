export type UploadProgressPhase = 'preparing' | 'uploading' | 'processing'

export type UploadProgressState = {
	phase: UploadProgressPhase
	loaded: number
	total: number | null
	percent: number | null
}

export type UploadProgressCallback = (progress: UploadProgressState) => void

function resolvePercent(loaded: number, total: number | null): number | null {
	if (!Number.isFinite(loaded) || loaded < 0) {
		return null
	}
	if (!Number.isFinite(total) || !total || total <= 0) {
		return null
	}
	return Math.max(0, Math.min(100, Math.round((loaded / total) * 100)))
}

export function emitUploadProgress(
	onProgress: UploadProgressCallback | undefined,
	phase: UploadProgressPhase,
	loaded: number,
	total: number | null = null
) {
	if (!onProgress) {
		return
	}

	onProgress({
		phase,
		loaded,
		total,
		percent: resolvePercent(loaded, total),
	})
}

export async function readFileAsBase64(
	file: File,
	onProgress?: UploadProgressCallback
): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		const knownSize = Number.isFinite(file.size) && file.size > 0 ? file.size : null

		emitUploadProgress(onProgress, 'preparing', 0, knownSize)

		reader.onprogress = event => {
			const total = event.lengthComputable ? event.total : knownSize
			emitUploadProgress(onProgress, 'preparing', event.loaded, total)
		}

		reader.onerror = () => reject(new Error('Unable to read file'))

		reader.onload = () => {
			emitUploadProgress(onProgress, 'preparing', knownSize || 0, knownSize)
			const result = typeof reader.result === 'string' ? reader.result : ''
			const parts = result.split(',')
			resolve(parts.length > 1 ? parts[1] : result)
		}

		reader.readAsDataURL(file)
	})
}
