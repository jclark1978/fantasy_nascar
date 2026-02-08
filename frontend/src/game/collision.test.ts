import { describe, expect, it } from 'vitest'
import { circleCircleCollision, circleRectCollision } from './collision'

describe('collision', () => {
  it('detects circle-rect overlap', () => {
    expect(circleRectCollision({ x: 15, y: 15 }, 10, { x: 20, y: 10, width: 40, height: 40, windows: [] })).toBe(
      true,
    )
    expect(circleRectCollision({ x: 0, y: 0 }, 5, { x: 20, y: 20, width: 10, height: 10, windows: [] })).toBe(false)
  })

  it('detects circle-circle overlap', () => {
    expect(circleCircleCollision({ x: 0, y: 0 }, 10, { x: 15, y: 0 }, 5)).toBe(true)
    expect(circleCircleCollision({ x: 0, y: 0 }, 10, { x: 50, y: 0 }, 5)).toBe(false)
  })
})
