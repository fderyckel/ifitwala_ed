import type { ClassHubWheelStudent } from '@/types/classHub'

export type ClassHubWheelPersistence = {
  persistent: boolean
  removed_student_ids: string[]
}

const STORAGE_PREFIX = 'ifw:class-wheel:'

function normalizeRemovedStudentIds(value: unknown) {
  if (!Array.isArray(value)) return []
  return Array.from(
    new Set(
      value
        .map((entry) => String(entry || '').trim())
        .filter(Boolean)
    )
  )
}

export function buildClassHubWheelStorageKey(studentGroup: string) {
  return `${STORAGE_PREFIX}${String(studentGroup || '').trim()}`
}

export function loadClassHubWheelPersistence(studentGroup: string): ClassHubWheelPersistence {
  if (typeof window === 'undefined' || !window.sessionStorage || !studentGroup) {
    return { persistent: false, removed_student_ids: [] }
  }

  try {
    const raw = window.sessionStorage.getItem(buildClassHubWheelStorageKey(studentGroup))
    if (!raw) return { persistent: false, removed_student_ids: [] }
    const parsed = JSON.parse(raw) as Partial<ClassHubWheelPersistence>
    return {
      persistent: Boolean(parsed?.persistent),
      removed_student_ids: normalizeRemovedStudentIds(parsed?.removed_student_ids),
    }
  } catch {
    return { persistent: false, removed_student_ids: [] }
  }
}

export function saveClassHubWheelPersistence(
  studentGroup: string,
  state: ClassHubWheelPersistence
) {
  if (typeof window === 'undefined' || !window.sessionStorage || !studentGroup) return

  window.sessionStorage.setItem(
    buildClassHubWheelStorageKey(studentGroup),
    JSON.stringify({
      persistent: Boolean(state.persistent),
      removed_student_ids: normalizeRemovedStudentIds(state.removed_student_ids),
    })
  )
}

export function clearClassHubWheelPersistence(studentGroup: string) {
  if (typeof window === 'undefined' || !window.sessionStorage || !studentGroup) return
  window.sessionStorage.removeItem(buildClassHubWheelStorageKey(studentGroup))
}

export function filterAvailableWheelStudents(
  students: ClassHubWheelStudent[],
  removedStudentIds: string[]
) {
  const removed = new Set(normalizeRemovedStudentIds(removedStudentIds))
  return (students || []).filter((student) => !removed.has(student.student))
}

export function secureRandomIndex(count: number) {
  if (!Number.isFinite(count) || count < 1) {
    throw new Error('count must be at least 1')
  }

  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const buffer = new Uint32Array(1)
    crypto.getRandomValues(buffer)
    return buffer[0] % count
  }

  return Math.floor(Math.random() * count)
}

function normalizeAngle(value: number) {
  const normalized = value % 360
  return normalized < 0 ? normalized + 360 : normalized
}

export function buildWheelTargetRotation(
  currentRotation: number,
  selectedIndex: number,
  segmentCount: number,
  fullTurns = 7
) {
  if (!Number.isFinite(segmentCount) || segmentCount < 1) {
    throw new Error('segmentCount must be at least 1')
  }

  const segmentAngle = 360 / segmentCount
  const centerAngle = selectedIndex * segmentAngle + segmentAngle / 2
  const targetAngle = normalizeAngle(360 - centerAngle)
  const currentAngle = normalizeAngle(currentRotation)

  let delta = targetAngle - currentAngle
  if (delta < 0) delta += 360

  return currentRotation + fullTurns * 360 + delta
}
