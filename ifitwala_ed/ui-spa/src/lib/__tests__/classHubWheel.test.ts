import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  buildClassHubWheelStorageKey,
  buildWheelTargetRotation,
  clearClassHubWheelPersistence,
  filterAvailableWheelStudents,
  loadClassHubWheelPersistence,
  saveClassHubWheelPersistence,
  secureRandomIndex,
} from '@/lib/classHubWheel'

describe('classHubWheel helpers', () => {
  afterEach(() => {
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('stores and loads persistent removed students per class', () => {
    saveClassHubWheelPersistence('SG-1', {
      persistent: true,
      removed_student_ids: ['STU-001', 'STU-002'],
    })

    expect(loadClassHubWheelPersistence('SG-1')).toEqual({
      persistent: true,
      removed_student_ids: ['STU-001', 'STU-002'],
    })

    clearClassHubWheelPersistence('SG-1')
    expect(window.sessionStorage.getItem(buildClassHubWheelStorageKey('SG-1'))).toBeNull()
  })

  it('filters removed students from the live wheel list', () => {
    const students = [
      { student: 'STU-001', student_name: 'Amina Dar' },
      { student: 'STU-002', student_name: 'Leo Mendez' },
      { student: 'STU-003', student_name: 'Priya Shah' },
    ]

    expect(filterAvailableWheelStudents(students, ['STU-002'])).toEqual([
      { student: 'STU-001', student_name: 'Amina Dar' },
      { student: 'STU-003', student_name: 'Priya Shah' },
    ])
  })

  it('builds a forward-only target rotation for the selected segment', () => {
    expect(buildWheelTargetRotation(0, 0, 4, 6)).toBe(2070)
    expect(buildWheelTargetRotation(30, 2, 6, 5)).toBeGreaterThan(30)
  })

  it('uses crypto-backed randomness when available', () => {
    const getRandomValues = vi.fn((buffer: Uint32Array) => {
      buffer[0] = 13
      return buffer
    })

    vi.stubGlobal('crypto', { getRandomValues })
    expect(secureRandomIndex(5)).toBe(3)
    expect(getRandomValues).toHaveBeenCalledOnce()
  })
})
